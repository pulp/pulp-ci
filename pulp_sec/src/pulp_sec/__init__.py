from pydantic_settings import BaseSettings, CliApp, CliSubCommand

from pulp_sec.bad import Bad
from pulp_sec.pypi import PyPi
from pulp_sec.report import Report


class PulpSec(BaseSettings, cli_parse_args=True, cli_implicit_flags=True):
    bad: CliSubCommand[Bad]
    pypi: CliSubCommand[PyPi]
    report: CliSubCommand[Report]

    def cli_cmd(self) -> None:
        CliApp.run_subcommand(self)


def main() -> None:
    CliApp.run(PulpSec)
