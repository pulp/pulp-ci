import urllib.request
from functools import cached_property

from packaging.version import Version
from pydantic import BaseModel, ConfigDict

from pulp_sec.common import Vulnerability


class OsvPackage(BaseModel):
    name: str
    ecosystem: str = "PyPI"


class OsvPayload(BaseModel):
    package: OsvPackage
    version: str


class OsvData(BaseModel):
    vulns: list[Vulnerability] = []

    model_config = ConfigDict(extra="allow")


class ReleaseInfo:
    def __init__(self, name: str, version: Version) -> None:
        self._name = name
        self._version = version

    @cached_property
    def _info(self) -> OsvData:
        payload = OsvPayload.model_validate(
            {"package": {"name": self._name}, "version": str(self._version)}
        )
        request = urllib.request.Request(
            "https://api.osv.dev/v1/query",
            method="POST",
            data=payload.model_dump_json().encode(),
        )
        with urllib.request.urlopen(request) as response:
            data = response.read()
        return OsvData.model_validate_json(data, context={"source": "OSV"})

    @cached_property
    def vulnerabilities(self) -> list[Vulnerability]:
        return self._info.vulns

    @cached_property
    def vulnerable(self) -> bool:
        return len(self.vulnerabilities) > 0
