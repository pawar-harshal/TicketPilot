"""
Thin, low-level wrapper around Python's built-in configparser.

This is deliberately the ONLY place configparser is touched. It does no
type conversion and knows nothing about what the values mean -- that is
Configuration.py's job, which reads through this module exactly once and
exposes typed constants. Nothing else in the codebase should import this
module directly.
"""
import configparser
import os
from functools import lru_cache

DEFAULT_CONFIG_PATH = os.environ.get(
    "TICKETPILOT_CONFIG_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "config.ini"),
)


@lru_cache(maxsize=1)
def load(path: str = DEFAULT_CONFIG_PATH) -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    read_files = parser.read(path)
    if not read_files:
        raise FileNotFoundError(
            f"Could not read config file at '{path}'. Fill in ticketpilot_das/data/config.ini "
            f"with real values, or set TICKETPILOT_CONFIG_PATH."
        )
    return parser


def get_section(section: str) -> dict:
    return dict(load().items(section))
