"""Modified version of utils.py from yapapi example scripts."""
# originally from https://github.com/golemfactory/yapapi/examples
import asyncio
import argparse
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import traceback
import sys

import colorama  # type: ignore

from yapapi import (
    Golem,
    windows_event_loop_fix,
    NoPaymentAccountError,
    __version__ as yapapi_version,
)
from yapapi.log import enable_default_logger


TEXT_COLOR_RED = "\033[31;1m"
TEXT_COLOR_GREEN = "\033[32;1m"
TEXT_COLOR_YELLOW = "\033[33;1m"
TEXT_COLOR_BLUE = "\033[34;1m"
TEXT_COLOR_MAGENTA = "\033[35;1m"
TEXT_COLOR_CYAN = "\033[36;1m"
TEXT_COLOR_WHITE = "\033[37;1m"

TEXT_COLOR_DEFAULT = "\033[0m"

colorama.init()


def build_parser(description: str) -> argparse.ArgumentParser:
    current_time_str = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S%z")
    tmpdir_as_path = Path(tempfile.gettempdir()) / "gcspyu_logs"
    tmpdir_as_path.mkdir(parents=True, exist_ok=True)
    default_log_as_path = tmpdir_as_path / f"{current_time_str}"
    default_log_path = str(default_log_as_path)
    # default_log_path = Path(tempfile.gettempdir()) / f"yapapi_{current_time_str}.log"

    parser = argparse.ArgumentParser(
        description=description, formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "--payment-driver",
        "--driver",
        help="Payment driver name, for example `erc20`",
        default="erc20",
    )
    parser.add_argument(
        "--payment-network",
        "--network",
        help="Payment network name, for example `rinkeby or polygon`",
        default="rinkeby",
    )
    parser.add_argument(
        "--subnet-tag",
        help="Subnet name, for example `devnet-beta or public-beta`",
        default="devnet-beta",
    )
    parser.add_argument(
        "--log-file",
        default=str(default_log_path),
        help="Log file for YAPAPI; default: %(default)s",
    )
    return parser


def format_usage(usage):
    return {
        "current_usage": usage.current_usage,
        "timestamp": usage.timestamp.isoformat(sep=" ") if usage.timestamp else None,
    }


def print_env_info(golem: Golem):
    print(
        f"yapapi version: {TEXT_COLOR_YELLOW}{yapapi_version}{TEXT_COLOR_DEFAULT}\n"
        f"Using subnet: {TEXT_COLOR_YELLOW}{golem.subnet_tag}{TEXT_COLOR_DEFAULT}, "
        f"payment driver: {TEXT_COLOR_YELLOW}{golem.payment_driver}{TEXT_COLOR_DEFAULT}, "
        f"and network: {TEXT_COLOR_YELLOW}{golem.payment_network}{TEXT_COLOR_DEFAULT}\n"
    )


def run_golem_example(spyu_coro, log_file=None):
    # This is only required when running on Windows with Python prior to 3.8:
    windows_event_loop_fix()

    if log_file:
        enable_default_logger(
            log_file=log_file,
            debug_activity_api=True,
            debug_market_api=True,
            debug_payment_api=True,
            debug_net_api=True,
        )

    loop = asyncio.get_event_loop()
    task = loop.create_task(spyu_coro)

    try:
        loop.run_until_complete(task)
    except NoPaymentAccountError as e:
        handbook_url = (
            "https://handbook.golem.network/requestor-tutorials/"
            "flash-tutorial-of-requestor-development"
        )
        print(
            f"{TEXT_COLOR_RED}"
            f"No payment account initialized for driver `{e.required_driver}` "
            f"and network `{e.required_network}`.\n\n"
            f"See {handbook_url} on how to initialize payment accounts for a requestor node."
            f"{TEXT_COLOR_DEFAULT}"
        )
    except KeyboardInterrupt:
        print(
            f"{TEXT_COLOR_YELLOW}"
            "Shutting down gracefully, please wait a short while "
            "or press Ctrl+C to exit immediately..."
            f"{TEXT_COLOR_DEFAULT}"
        )
        task.cancel()
        try:
            loop.run_until_complete(task)
            print(
                f"{TEXT_COLOR_YELLOW}"
                f"Shutdown completed, thank you for waiting!{TEXT_COLOR_DEFAULT}")
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass
    except Exception as e:
        # tb=sys.exc_info()[2]
        print(f"\033[1mEXCEPTION:\033[0m\n")
        print(f"{traceback.print_exc()}")

    else:
        return task.result()
