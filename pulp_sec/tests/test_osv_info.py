import pytest
from packaging.version import Version

from pulp_sec.osv import ReleaseInfo


@pytest.fixture(scope="class")
def osv_info_1() -> ReleaseInfo:
    return ReleaseInfo("a", Version("1.0"))


@pytest.fixture(scope="class")
def osv_info_2() -> ReleaseInfo:
    return ReleaseInfo("a", Version("2.0"))


class TestOsvInfo:
    def test_a_1_is_vulnerable(self, osv_info_1: ReleaseInfo) -> None:
        assert osv_info_1.vulnerable

    def test_a_2_is_not_vulnerable(self, osv_info_2: ReleaseInfo) -> None:
        assert not osv_info_2.vulnerable

    def test_a_1_vulnerabilities_contains_entries(
        self, osv_info_1: ReleaseInfo
    ) -> None:
        assert len(osv_info_1.vulnerabilities) == 2
        assert osv_info_1.vulnerabilities[1].id == "cvpulp0001"

    def test_a_2_vulnerabilities_is_empty(self, osv_info_2: ReleaseInfo) -> None:
        assert len(osv_info_2.vulnerabilities) == 0

    def test_vulnerability_is_annotated_with_source(
        self, osv_info_1: ReleaseInfo
    ) -> None:
        assert osv_info_1.vulnerabilities[0]._source == "OSV"

    def test_unknown_package(self) -> None:
        assert ReleaseInfo("unknown", Version("1.2.3")).vulnerable is False
