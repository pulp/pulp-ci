from pathlib import Path

import pytest
from packaging.requirements import Requirement
from packaging.version import Version

from pulp_sec.pypi import PackageInfo
from pulp_sec.repo_info import ReleaseInfo, RepoInfo


@pytest.fixture(scope="session")
def repo_info(repo_path: Path) -> RepoInfo:
    # Let the working directory say something else than upstream.
    (repo_path / "template_config.yml").write_text("""---
plugin_default_branch: "principal"
latest_release_branch: "4.3"
...""")
    return RepoInfo()


class TestRepoInfo:
    def test_template_config(self, repo_info: RepoInfo) -> None:
        assert repo_info.template_config.plugin_default_branch == "principal"
        assert repo_info.template_config.latest_release_branch == "4.5"

    def test_empty_repo_has_supported_branches_main(self, repo_info: RepoInfo) -> None:
        assert repo_info.supported_branches == ["principal", "6.0", "4.5", "3.5", "3.4"]

    def test_provides_package_info(self, repo_info: RepoInfo) -> None:
        assert isinstance(repo_info.package_info("a"), PackageInfo)


class TestBranchInfo:
    def test_has_dependencies(self, repo_info: RepoInfo) -> None:
        branch_info = repo_info.branches["principal"]
        assert branch_info.dependencies == [Requirement("a>=1.0.0,<2")]

    def test_old_branch_has_dependencies(self, repo_info: RepoInfo) -> None:
        branch_info = repo_info.branches["3.4"]
        assert branch_info.dependencies == [Requirement("ra>=1.2.3,<3")]

    def test_provides_info_about_the_dependencies(self, repo_info: RepoInfo) -> None:
        branch_info = repo_info.branches["principal"]
        dependency_info = branch_info.dependency_infos[0]
        assert dependency_info.target_version == Version("1.1")
        assert dependency_info.target_release.vulnerable
        assert len(dependency_info.target_release.vulnerabilities) == 3


class TestDependencyInfo:
    def test_has_name(self, repo_info: RepoInfo) -> None:
        dependency_info = repo_info.branches["principal"].dependency_infos[0]
        assert dependency_info.name == "a"

    def test_describes_matching_versions(self, repo_info: RepoInfo) -> None:
        dependency_info = repo_info.branches["principal"].dependency_infos[0]
        assert dependency_info.matching_versions == [Version("1.0"), Version("1.1")]
        assert dependency_info.target_version == Version("1.1")

    def test_describes_possible_updates(self, repo_info: RepoInfo) -> None:
        dependency_info = repo_info.branches["principal"].dependency_infos[0]
        assert dependency_info.update_versions == [Version("2.0")]

    def test_provides_release_infos(self, repo_info: RepoInfo) -> None:
        dependency_info = repo_info.branches["principal"].dependency_infos[0]
        assert isinstance(dependency_info.matching_releases[-1], ReleaseInfo)
