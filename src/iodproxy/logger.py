"""
A small logger wrapper around logfire.
"""

import os
import uuid
from functools import partial, wraps
from pathlib import Path
from typing import TYPE_CHECKING, Any, Sequence

import logfire
from logfire import LevelName, Logfire
from omproxy import __version__

if TYPE_CHECKING:
    from logfire._internal.main import ExcInfo

# TODO: (use auth see https://github.com/pydantic/logfire/issues/651#issuecomment-2522714987)
os.environ["LOGFIRE_TOKEN"] = "BHVQS0FylRTlf3j50WHNzh8S6ypPCJ308cjcyrdNp3Jc"
os.environ["LOGFIRE_PROJECT_NAME"] = "iod-mcp"
os.environ["LOGFIRE_PROJECT_URL"] = "https://logfire.pydantic.dev/grll/iod-mcp"
os.environ["LOGFIRE_API_URL"] = "https://logfire-api.pydantic.dev"


def get_or_create_unique_device_id():
    """
    Get or create a unique device id.
    store the id in the user home directory.
    """
    path = Path.home() / ".iod" / ".unique_device_id"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(uuid.uuid4()))
    return path.read_text()


UNIQUE_DEVICE_ID = get_or_create_unique_device_id()


def get_logger(mcp_server_name: str, **logfire_configure_kwargs) -> Logfire:
    """
    Setup a logfire logger with the given mcp server name.
    it automatically adds unique device id to every log and span call.
    """
    logger = logfire.configure(
        service_name="iodproxy",
        service_version=__version__,
        console=False,
        local=True,
        **logfire_configure_kwargs,
    ).with_tags(mcp_server_name)

    # we make sure every log call has the unique device id
    original_log = logger.log

    @wraps(original_log)
    def log_with_device_id(
        level: LevelName | int,
        msg_template: str,
        attributes: dict[str, Any] | None = None,
        tags: Sequence[str] | None = None,
        exc_info: "ExcInfo" = False,
        console_log: bool | None = None,
    ) -> None:
        merged_attributes = {"unique_device_id": UNIQUE_DEVICE_ID}
        if attributes:
            merged_attributes.update(attributes)
        return original_log(
            level,
            msg_template,
            attributes=merged_attributes,
            tags=tags,
            exc_info=exc_info,
            console_log=console_log,
        )

    logger.log = log_with_device_id
    logger.span = partial(logger.span, unique_device_id=UNIQUE_DEVICE_ID)
    return logger
