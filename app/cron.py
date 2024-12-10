import argparse
import logging
from typing import Any, Protocol

import inject

from app import application
from app.config import Config

logger = logging.getLogger(__name__)


class CronCommand(Protocol):
    def init_arguments(self, subparser: Any) -> None: ...

    def run(self, args: argparse.Namespace) -> int: ...


CRON_COMMANDS: dict[str, CronCommand] = {}


def main() -> None:
    config: Config = get_config()
    application.setup_logging(config)

    parser = argparse.ArgumentParser(description="Cron command line interface")
    subparser = parser.add_subparsers(dest="command", title="cron commands", help="valid cron commands", required=True)
    for name in CRON_COMMANDS.keys():
        command_get(name).init_arguments(subparser)

    args = parser.parse_args()

    # Run command
    logger.info("Running command %s", args.command)
    code = command_get(args.command).run(args)
    exit(code)


def command_exists(name: str) -> bool:
    return name in CRON_COMMANDS


def command_get(name: str) -> CronCommand:
    return inject.instance(CRON_COMMANDS[name])


def get_config() -> Config:
    return inject.instance(Config)


if __name__ == "__main__":
    main()
