"""
A small logger wrapper around logfire.
"""

import os
import uuid
from pathlib import Path
from typing import Any

import logfire
from omproxy import __version__

# TODO: (use auth see https://github.com/pydantic/logfire/issues/651#issuecomment-2522714987)
os.environ["LOGFIRE_TOKEN"] = "BHVQS0FylRTlf3j50WHNzh8S6ypPCJ308cjcyrdNp3Jc"
os.environ["LOGFIRE_PROJECT_NAME"] = "iod-mcp"
os.environ["LOGFIRE_PROJECT_URL"] = "https://logfire.pydantic.dev/grll/iod-mcp"
os.environ["LOGFIRE_API_URL"] = "https://logfire-api.pydantic.dev"


def get_or_create_unique_device_id():
    path = Path.home() / ".iod" / ".unique_device_id"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(uuid.uuid4()))
    return path.read_text()


class Logger:
    """
    A small logger wrapper around logfire.

    it initializes with good configuration for iod proxy and adds necessary tags and attributes
    on the different log level calls.
    """

    def __init__(self, mcp_server_name: str, **logfire_configure_kwargs: Any):
        self.mcp_server_name = mcp_server_name
        self.unique_device_id = get_or_create_unique_device_id()
        self.logger = logfire.configure(
            service_name="iodproxy",
            service_version=__version__,
            console=False,
            local=True,
            **logfire_configure_kwargs,
        ).with_tags(self.mcp_server_name)

    def error(self, message: str, **kwargs):
        self.logger.error(message, **kwargs, unique_device_id=self.unique_device_id)

    def warn(self, message: str, **kwargs):
        self.logger.warn(message, **kwargs, unique_device_id=self.unique_device_id)

    def info(self, message: str, **kwargs):
        self.logger.info(message, **kwargs, unique_device_id=self.unique_device_id)

    def debug(self, message: str, **kwargs):
        self.logger.debug(message, **kwargs, unique_device_id=self.unique_device_id)

    def trace(self, message: str, **kwargs):
        self.logger.trace(message, **kwargs, unique_device_id=self.unique_device_id)

    def exception(self, message: str, **kwargs):
        self.logger.exception(message, **kwargs, unique_device_id=self.unique_device_id)

    def fatal(self, message: str, **kwargs):
        self.logger.fatal(message, **kwargs, unique_device_id=self.unique_device_id)

    def notice(self, message: str, **kwargs):
        self.logger.notice(message, **kwargs, unique_device_id=self.unique_device_id)
