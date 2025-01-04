import asyncio
import os
from typing import Literal

from mcp.client.stdio import StdioServerParameters
from mcp.types import (
    JSONRPCError,
    JSONRPCMessage,
    JSONRPCNotification,
    JSONRPCRequest,
    JSONRPCResponse,
)
from omproxy.proxy import StdioProxy

from iodproxy.logger import get_logger


class IODProxy(StdioProxy):
    def __init__(self, mcp_server_name: str, timeout: float = 60 * 5):
        """Initialize the proxy with the given MCP server name.

        Args:
            mcp_server_name: The name of the MCP server proxied.
        """
        super().__init__()
        self.logger = get_logger(mcp_server_name)
        self.timeout = timeout

        self.active_requests: dict[str, tuple[asyncio.Task, asyncio.Future]] = {}
        self.already_logged_methods: set[str] = set()
        self.responses_to_ignore: set[str | int] = set()

    async def _handle_request(
        self,
        initiator: Literal["client", "server"],
        request: JSONRPCRequest,
        future: asyncio.Future[JSONRPCResponse | JSONRPCError],
    ):
        """an async function running as a concurrent task per request to enable better logging"""
        with self.logger.span(
            f"MCP {initiator} request #{request.id}: '{request.method}'",
            json_rpc_request=request,
        ):
            try:
                response = await asyncio.wait_for(future, timeout=self.timeout)
                if isinstance(response, JSONRPCError):
                    self.logger.error(
                        "error received",
                        json_rpc_error=response,
                    )
                else:
                    if "isError" in response.result and response.result["isError"]:
                        self.logger.error(
                            "error received",
                            json_rpc_error=response,
                        )
                    else:
                        self.logger.info(
                            "response received",
                            json_rpc_response=response,
                        )
            except asyncio.TimeoutError:
                self.logger.error(f"request timed out after {self.timeout} seconds")
            except asyncio.CancelledError:
                # Normal cancellation
                pass
            finally:
                self.active_requests.pop(request.id, None)

    def _process_message(
        self, initiator: Literal["client", "server"], message: JSONRPCMessage
    ):
        if isinstance(message.root, JSONRPCRequest):
            # spawn a coroutine awaiting a response
            future = asyncio.Future()
            task = asyncio.create_task(
                self._handle_request(initiator, message.root, future)
            )
            self.active_requests[message.root.id] = (task, future)

        elif isinstance(message.root, JSONRPCResponse) or isinstance(
            message.root, JSONRPCError
        ):
            try:
                _, future = self.active_requests[message.root.id]
                future.set_result(message.root)
            except KeyError:
                self.logger.error(
                    f"Request {message.root.id} not found in active requests.",
                    _exc_info=KeyError,
                )
                self.logger.info(
                    "orphan response or error received",
                    json_rpc_response_or_error=message.root,
                )

        elif isinstance(message.root, JSONRPCNotification):
            self.logger.info(
                f"MCP {initiator} notification: '{message.root.method}'",
                json_rpc_notification=message.root,
            )

        else:
            self.logger.info("unknown message type received", json_rpc_message=message)

    def _on_mcp_client_message(self, message: JSONRPCMessage):
        """can be used to handle messages from the MCP client"""

        # Claude Desktop App is polling for resources/list and prompts/list
        # we just log the first request to avoid spamming logfire with useless logs
        if isinstance(message.root, JSONRPCRequest):
            method = message.root.method
            if method in ["resources/list", "prompts/list"]:
                if method in self.already_logged_methods:
                    self.responses_to_ignore.add(message.root.id)
                    return
                self.already_logged_methods.add(method)

        self._process_message("client", message)

    def _on_mcp_server_message(self, message: JSONRPCMessage | Exception):
        """can be used to handle messages from the MCP server"""
        if isinstance(message, Exception):
            self.logger.error(
                "Exception object received from MCP Server.", _exc_info=message
            )
        else:  # JSONRPCMessage
            # Claude Desktop App is polling for resources/list and prompts/list
            # we just log the first request to avoid spamming logfire with useless logs
            if isinstance(message.root, JSONRPCResponse) or isinstance(
                message.root, JSONRPCError
            ):
                id = message.root.id
                if id in self.responses_to_ignore:
                    self.responses_to_ignore.remove(id)
                    return

            self._process_message("server", message)

    def _on_start(self):
        """can be used to handle the start of the proxy"""
        self.logger.info("starting proxy")

    def _on_close(self):
        """can be used to handle the close of the proxy"""
        self.logger.info("closing proxy")


if __name__ == "__main__":
    proxy = IODProxy("echo")

    with proxy.logger.span("proxy session") as span:
        proxy.run(
            StdioServerParameters(
                command="uv", args=["run", "src/echo.py"], env=os.environ
            )
        )
