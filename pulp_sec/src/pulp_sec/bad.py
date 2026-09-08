# TODO
# * optional dependencies
# * suggest updates
# * compare with vulnerability database

import typing as t

from packaging.requirements import canonicalize_name
from pydantic import BaseModel, BeforeValidator
from pydantic_settings import CliPositionalArg

from pulp_sec.repo_info import RepoInfo


class Bad(BaseModel):
    """Check project for a bad apple dependency."""

    dependency: CliPositionalArg[
        t.Annotated[str, BeforeValidator(canonicalize_name)] | None
    ] = None

    def cli_cmd(self) -> None:
        repo_info = RepoInfo()
        for branch in repo_info.supported_branches:
            print(f"[{branch}]:")
            branch_info = repo_info.branches[branch]
            for dep in branch_info.dependency_infos:
                if self.dependency is None or self.dependency == dep.name:
                    rel = dep.target_release
                    vuln = "V" if rel.vulnerable else " "
                    print(f" [{vuln}]  {dep} => {dep.target_version}")
                    if rel.vulnerable:
                        v_ids = ", ".join(v.id for v in rel.vulnerabilities)
                        print(f"  ⤷    {v_ids}")
