from mcp.client.stdio import StdioServerParameters
from mcp.types import JSONRPCMessage
from omproxy.proxy import StdioProxy

from iodproxy.logger import get_logger


class IODProxy(StdioProxy):
    def __init__(self, mcp_server_name: str):
        """Initialize the proxy with the given MCP server name.

        Args:
            mcp_server_name: The name of the MCP server proxied.
        """
        super().__init__()
        self.logger = get_logger(mcp_server_name)

    def _on_mcp_client_message(self, message: JSONRPCMessage):
        """can be used to handle messages from the MCP client"""
        self.logger.info(
            "forwarding MCP Client message to MCP server.", json_rpc_message=message
        )

    def _on_mcp_server_message(self, message: JSONRPCMessage | Exception):
        """can be used to handle messages from the MCP server"""
        if isinstance(message, Exception):
            self.logger.error(
                "An Exception object was sent from MCP server.", _exc_info=message
            )
        else:  # JSONRPCMessage
            self.logger.info(
                "forwarding MCP Server message to MCP Client.", json_rpc_message=message
            )

    def _on_start(self):
        """can be used to handle the start of the proxy"""
        self.logger.info("starting proxy")

    def _on_close(self):
        """can be used to handle the close of the proxy"""
        self.logger.info("closing proxy")


if __name__ == "__main__":
    proxy = IODProxy("echo")

    with proxy.logger.span("proxy session"):
        proxy.run(
            StdioServerParameters(
                command="uv",
                args=["run", "src/echo.py"],
            )
        )
