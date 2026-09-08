import shlex
import subprocess
import tomllib
from functools import cache, cached_property
from pathlib import Path

import yaml
from packaging.requirements import Requirement, canonicalize_name
from packaging.version import Version
from pydantic import BaseModel

from pulp_sec import osv, pypi
from pulp_sec.common import Vulnerability


class TemplateConfig(BaseModel):
    plugin_default_branch: str = "main"
    latest_release_branch: str | None = None
    supported_release_branches: list[str] = []


class RepoInfo:
    """
    Lazily collect and cache info about the repository in the current dir.
    """

    def __init__(self):
        # This makes the cache part of the instance after binding self.
        # This avoids being a memory leak.
        # TODO Look if this is really the best scope to cahce these.
        # When looking into multiple repositories package data may still be shared.
        self.package_info = cache(self._package_info)
        self.pypi_info = cache(self._pypi_info)
        self.osv_info = cache(self._osv_info)

    @cached_property
    def template_config(self) -> TemplateConfig:
        current_template_config = TemplateConfig.model_validate(
            yaml.safe_load(Path("template_config.yml").read_text())
        )
        default_branch = shlex.quote(current_template_config.plugin_default_branch)
        template_config_yml = subprocess.check_output(
            ["git", "show", f"upstream/{default_branch}:template_config.yml"]
        )
        return TemplateConfig.model_validate(yaml.safe_load(template_config_yml))

    @cached_property
    def supported_branches(self) -> list[str]:
        branches = set(self.template_config.supported_release_branches)
        if self.template_config.latest_release_branch is not None:
            branches.add(self.template_config.latest_release_branch)
        return [
            self.template_config.plugin_default_branch,
            *sorted(branches, key=Version, reverse=True),
        ]

    @cached_property
    def branches(self) -> dict[str, BranchInfo]:
        return {b: BranchInfo(self, b) for b in self.supported_branches}

    def _package_info(self, name: str) -> pypi.PackageInfo:
        return pypi.PackageInfo(name)

    def _pypi_info(self, name: str, version: Version) -> pypi.ReleaseInfo:
        return pypi.ReleaseInfo(name, version)

    def _osv_info(self, name: str, version: Version) -> osv.ReleaseInfo:
        return osv.ReleaseInfo(name, version)


def _strip_comment(req: str) -> str:
    return req.split("#", maxsplit=1)[0].strip()


class BranchInfo:
    """
    Lazily collect and cache info about a certain branch in the current repo.
    Do not change the working directory at all.
    """

    def __init__(self, repo_info: RepoInfo, branch: str):
        self._repo_info = repo_info
        self._branch = shlex.quote(branch)

    @cached_property
    def dependencies(self) -> list[Requirement]:
        try:
            # Try the modern approach.
            pyproject_toml = subprocess.check_output(
                ["git", "show", f"upstream/{self._branch}:pyproject.toml"]
            ).decode()
            pyproject = tomllib.loads(pyproject_toml)
            dependencies = pyproject["project"]["dependencies"]
        except subprocess.CalledProcessError, KeyError:
            # Fall back to old requirements.txt.
            requirements_txt = subprocess.check_output(
                ["git", "show", f"upstream/{self._branch}:requirements.txt"]
            ).decode()
            dependencies = [
                _strip_comment(line) for line in requirements_txt.splitlines()
            ]

        return [Requirement(line) for line in dependencies if line != ""]

    @cached_property
    def dependency_infos(self) -> list[DependencyInfo]:
        return [DependencyInfo(self._repo_info, dep) for dep in self.dependencies]


class DependencyInfo:
    def __init__(self, repo_info: RepoInfo, dependency: Requirement):
        self._repo_info = repo_info
        self._dependency = dependency
        self._package_info = repo_info.package_info(dependency.name)

    def __str__(self):
        return str(self._dependency)

    @cached_property
    def matching_versions(self) -> list[Version]:
        return [
            v for v in self._package_info.versions if v in self._dependency.specifier
        ]

    @cached_property
    def matching_releases(self) -> list[ReleaseInfo]:
        return [
            ReleaseInfo(self._repo_info, self._dependency.name, v)
            for v in self.matching_versions
        ]

    @property
    def target_version(self) -> Version:
        return self.matching_versions[-1]

    @property
    def target_release(self) -> ReleaseInfo:
        return self.matching_releases[-1]

    @cached_property
    def update_versions(self) -> list[Version]:
        return [v for v in self._package_info.versions if v > self.target_version]

    @property
    def updates(self) -> bool:
        return len(self.update_versions) > 0

    @property
    def name(self) -> str:
        return canonicalize_name(self._dependency.name)


class ReleaseInfo:
    def __init__(self, repo_info: RepoInfo, name: str, version: Version):
        self._repo_info = repo_info
        self.name = name
        self.version = version
        self._pypi_info = repo_info.pypi_info(name, version)
        self._osv_info = repo_info.osv_info(name, version)

    @cached_property
    def vulnerabilities(self) -> list[Vulnerability]:
        # TODO consolidate these entries with their aliases.
        return self._pypi_info.vulnerabilities + self._osv_info.vulnerabilities

    @property
    def vulnerable(self) -> bool:
        return len(self.vulnerabilities) > 0
