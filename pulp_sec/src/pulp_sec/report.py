from pydantic import BaseModel

from pulp_sec.repo_info import RepoInfo


class Report(BaseModel):
    """Make a summary over vulnerable and outdated dependencies."""

    vulnerable: bool = True
    update: bool = False

    def cli_cmd(self) -> None:
        repo_info = RepoInfo()
        for branch in repo_info.branches:
            print(f"[{branch}]:")
            branch_info = repo_info.branches[branch]
            for dep in branch_info.dependency_infos:
                marker = ""
                dump = False
                if self.update:
                    if dep.updates:
                        dump = True
                        marker += "U"
                    else:
                        marker += " "
                if self.vulnerable:
                    if dep.target_release.vulnerable:
                        dump = True
                        marker += "V"
                    else:
                        marker += " "
                if dump:
                    print(marker, dep, dep.target_version)
