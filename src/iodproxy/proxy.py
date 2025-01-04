import asyncio
from typing import Literal

from mcp.client.stdio import StdioServerParameters
from mcp.types import (
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

    async def _handle_request(
        self,
        initiator: Literal["client", "server"],
        request: JSONRPCRequest,
        future: asyncio.Future[JSONRPCResponse],
    ):
        """an async function running as a concurrent task per request to enable better logging"""
        with self.logger.span(
            f"MCP {initiator} request: '{request.method}'",
            json_rpc_request=request,
        ):
            try:
                response = await asyncio.wait_for(future, timeout=self.timeout)
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

        elif isinstance(message.root, JSONRPCResponse):
            try:
                _, future = self.active_requests[message.root.id]
                future.set_result(message.root)
            except KeyError:
                self.logger.error(
                    f"Request {message.root.id} not found in active requests.",
                    _exc_info=KeyError,
                )
                self.logger.info(
                    "orphan response received", json_rpc_response=message.root
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
        self._process_message("client", message)

    def _on_mcp_server_message(self, message: JSONRPCMessage | Exception):
        """can be used to handle messages from the MCP server"""
        if isinstance(message, Exception):
            self.logger.error(
                "Exception object received from MCP Server.", _exc_info=message
            )
        else:  # JSONRPCMessage
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
                command="uv",
                args=["run", "src/echo.py"],
            )
        )
