from packaging.version import Version

from pulp_sec.pypi import PackageInfo


def test_pypi_info_has_versions() -> None:
    assert PackageInfo("a").versions == [Version("1.0"), Version("1.1"), Version("2.0")]


def test_pypi_info_releases() -> None:
    vulnerability = PackageInfo("a").releases[Version("1.0")].vulnerabilities[0]
    assert vulnerability.id == "pulpcv0000"
    assert vulnerability.aliases == ["cvpulp0001"]
    assert vulnerability._source == "PyPI"
