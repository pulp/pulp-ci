"""
Module containing the PyPI specific data gathering classes.
"""

import typing as t
from functools import cached_property
from urllib import parse, request

from packaging.requirements import SpecifierSet, canonicalize_name
from packaging.version import Version
from pydantic import BaseModel, BeforeValidator, ConfigDict
from pydantic_settings import CliPositionalArg

from pulp_sec.common import Vulnerability


class PackageData(BaseModel):
    releases: dict[str, t.Any]
    vulnerabilities: list[Vulnerability]

    model_config = ConfigDict(extra="allow")


class ReleaseData(BaseModel):
    vulnerabilities: list[Vulnerability]

    model_config = ConfigDict(extra="allow")


class PackageInfo:
    def __init__(self, name: str):
        self._name = parse.quote(canonicalize_name(name))

    @cached_property
    def package_info(self) -> PackageData:
        with request.urlopen(f"https://pypi.org/pypi/{self._name}/json/") as response:
            data = response.read()
        return PackageData.model_validate_json(data)

    @cached_property
    def versions(self) -> list[Version]:
        return sorted([Version(v) for v in self.package_info.releases])

    @cached_property
    def releases(self) -> dict[Version, ReleaseInfo]:
        return {v: ReleaseInfo(self._name, v) for v in self.versions}


class ReleaseInfo:
    def __init__(self, name: str, version: Version):
        self._name = name
        self._version = version

    @cached_property
    def release_info(self) -> ReleaseData:
        with request.urlopen(
            f"https://pypi.org/pypi/{self._name}/{self._version}/json/"
        ) as response:
            data = response.read()
        return ReleaseData.model_validate_json(data, context={"source": "PyPI"})

    @cached_property
    def vulnerabilities(self) -> list[Vulnerability]:
        return self.release_info.vulnerabilities

    @cached_property
    def vulnerable(self) -> bool:
        return len(self.vulnerabilities) > 0


class PyPi(BaseModel):
    """Dump PyPi info about dependency."""

    dependency: CliPositionalArg[t.Annotated[str, BeforeValidator(canonicalize_name)]]
    version: CliPositionalArg[str | None] = None

    def cli_cmd(self) -> None:
        package_info = PackageInfo(self.dependency)
        if self.version is not None:
            specifier = SpecifierSet(self.version)
        else:
            specifier = SpecifierSet("")
        for version in package_info.versions:
            if version in specifier:
                release = package_info.releases[version]
                print(version)
                for vulnerability in release.vulnerabilities:
                    aliases = ", ".join(vulnerability.aliases)
                    print(f"  {vulnerability.id} ({aliases})")
