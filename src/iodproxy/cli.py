import argparse
import os

from mcp.client.stdio import StdioServerParameters

from iodproxy.proxy import IODProxy


def main():
    parser = argparse.ArgumentParser(
        description="Launch an IOD MCP proxy for a given command"
    )
    parser.add_argument(
        "--name",
        help="Name of the MCP server being proxied",
        required=True,
    )
    parser.add_argument(
        "command",
        help="The command to execute",
    )
    parser.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        default=[],
        help="Additional arguments to pass to the command",
    )

    args = parser.parse_args()

    proxy = IODProxy(args.name)

    with proxy.logger.span("proxy session"):
        proxy.run(
            StdioServerParameters(
                command=args.command,
                args=args.args,
                env=os.environ,
            )
        )


if __name__ == "__main__":
    main()
