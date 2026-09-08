import contextlib
import json
import subprocess
import typing as t
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request

import pytest

from pulp_sec.osv import OsvPayload

TEMPLATE_CONFIG_YML = """
---
plugin_default_branch: "principal"
latest_release_branch: "4.5"
supported_release_branches:
  - "6.0"
  - "3.4"
  - "3.5"
"""

PYPROJECT_TOML = """
[project]
dependencies = [
  "a>=1.0.0,<2",
]
"""

REQUIREMENTS_TXT = """
ra<3,>=1.2.3  # Comment
"""

PYPI_GET_RESPONSES: dict[str, tuple[int, str | None]] = {
    "/pypi/a/json/": (
        200,
        json.dumps(
            {"releases": {"1.0": {}, "1.1": {}, "2.0": {}}, "vulnerabilities": []}
        ),
    ),
    "/pypi/a/1.0/json/": (
        200,
        json.dumps(
            {"vulnerabilities": [{"id": "pulpcv0000", "aliases": ["cvpulp0001"]}]}
        ),
    ),
    "/pypi/a/1.1/json/": (
        200,
        json.dumps(
            {"vulnerabilities": [{"id": "pulpcv0000", "aliases": ["cvpulp0001"]}]}
        ),
    ),
}


OSV_DEV_RESPONSES: dict[tuple[str, str], tuple[int, str | None]] = {
    ("a", "1.0"): (
        200,
        json.dumps(
            {
                "vulns": [
                    {"id": "cvpulp0000", "aliases": ["pulpcv0001"]},
                    {"id": "cvpulp0001", "aliases": []},
                ]
            }
        ),
    ),
    ("a", "1.1"): (
        200,
        json.dumps(
            {
                "vulns": [
                    {"id": "cvpulp0000", "aliases": ["pulpcv0001"]},
                    {"id": "cvpulp0001", "aliases": []},
                ]
            }
        ),
    ),
    ("a", "2.0"): (
        200,
        json.dumps({"vulns": []}),
    ),
}


@pytest.fixture(scope="session")
def repo_path(tmp_path_factory: pytest.TempPathFactory) -> t.Iterator[Path]:
    # Create a fake git repository to experiment on.
    # Register itself as it's own "upstream" remote.
    repo_path = tmp_path_factory.mktemp("test_repository")
    with contextlib.chdir(repo_path):
        subprocess.check_output(["git", "init", "--initial-branch", "principal"])

        # Prepare the release branches.
        (repo_path / "template_config.yml").write_text(TEMPLATE_CONFIG_YML)
        (repo_path / "requirements.txt").write_text(REQUIREMENTS_TXT)

        subprocess.check_output(
            ["git", "add", "template_config.yml", "requirements.txt"]
        )
        subprocess.check_output(
            ["git", "commit", "--no-gpg-sign", "-m", "Initial commit"]
        )
        subprocess.check_output(["git", "branch", "3.4"])
        subprocess.check_output(["git", "branch", "3.5"])

        (repo_path / "requirements.txt").unlink()
        (repo_path / "pyproject.toml").write_text(PYPROJECT_TOML)

        subprocess.check_output(
            ["git", "add", "template_config.yml", "pyproject.toml", "requirements.txt"]
        )
        subprocess.check_output(
            ["git", "commit", "--no-gpg-sign", "-m", "Update to pyproject"]
        )
        subprocess.check_output(["git", "branch", "4.5"])
        subprocess.check_output(["git", "branch", "6.0"])

        subprocess.check_output(["git", "remote", "add", "upstream", "."])
        subprocess.check_output(["git", "fetch", "upstream"])

        yield repo_path


class MockResponse:
    def __init__(self, status: int, body: str | None):
        self.status = status
        self._body = body

    def __enter__(self) -> t.Self:
        return self

    def __exit__(self, *args: object):
        pass

    def read(self) -> str | None:
        return self._body


def mock_urlopen(url: str | Request) -> MockResponse:
    if isinstance(url, str):
        url = Request(url, method="GET")

    o = urlsplit(url.full_url)
    assert o.scheme == "https"
    if o.netloc == "pypi.org":
        assert url.method == "GET"
        try:
            status, body = PYPI_GET_RESPONSES[o.path]
        except KeyError:
            pytest.fail(f"Unexpected url: {url}")
    elif o.netloc == "api.osv.dev":
        assert url.method == "POST"
        assert o.path == "/v1/query"
        assert isinstance(url.data, bytes)
        payload = OsvPayload.model_validate_json(url.data)
        try:
            status, body = OSV_DEV_RESPONSES[(payload.package.name, payload.version)]
        except KeyError:
            status, body = 200, "{}"
    else:
        pytest.fail(f"Unexpected request: {url}")
    return MockResponse(status, body)


@pytest.fixture(autouse=True)
def mock_pypi(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", mock_urlopen)
