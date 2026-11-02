"""MCP Server for VDS Platform operations.

Based on MCP Python SDK v1.0.0+
Context7: /modelcontextprotocol/python-sdk
Key Features: FastMCP, tool registration, stdio transport
"""

import subprocess
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from .config import load_settings
from .tools import (
    register_bitbucket_tools,
    register_confluence_tools,
    register_git_tools,
    register_jira_tools,
    register_vidp_tools,
)

# Initialize FastMCP server
mcp = FastMCP("VDS Orchestrator")


async def execute_vds_cli(*args: str) -> dict[str, Any]:
    """Execute VDS CLI command via subprocess.

    Args:
        *args: Command arguments to pass to vds-cli

    Returns:
        dict: Command execution result with stdout, stderr, returncode
    """
    cmd = ["vds-cli", *list(args)]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }


# Register all tool modules
register_jira_tools(mcp, execute_vds_cli)
register_confluence_tools(mcp, execute_vds_cli)
register_bitbucket_tools(mcp, execute_vds_cli)
register_git_tools(mcp, execute_vds_cli)
register_vidp_tools(mcp, execute_vds_cli)


try:
    import typer

    app = typer.Typer(
        name="vds-mcp-server",
        help="VDS MCP Server — stdio Model Context Protocol server for VDS platform operations.",
        add_completion=False,
        no_args_is_help=False,
    )

    @app.callback(invoke_without_command=True)
    def _root(ctx: typer.Context) -> None:
        """Default behavior: start the FastMCP server over stdio transport.

        Requires shared VDS environment configuration to be available.
        """
        if ctx.invoked_subcommand is not None:
            return
        load_settings()
        mcp.run()

    @app.command()
    def serve() -> None:
        """Start the FastMCP server over stdio transport (explicit form)."""
        load_settings()
        mcp.run()

    def main() -> None:
        """Main entry point for MCP server (Typer-wrapped for help-output consistency)."""
        app()

except ImportError:
    # Fallback to argparse-style if typer is unavailable (extreme edge case;
    # typer is in pyproject.toml core deps, but defensive is better than broken).
    def main() -> None:  # type: ignore[no-redef]
        """Main entry point for MCP server (argparse fallback)."""
        if any(arg in {"-h", "--help", "help"} for arg in sys.argv[1:]):
            print("Usage: vds-mcp-server [OPTIONS]")
            print()
            print("VDS MCP Server - stdio Model Context Protocol server for VDS platform operations")
            print()
            print("Options:")
            print("  -h, --help  Show this message and exit.")
            print()
            print("Behavior:")
            print("  Starts the FastMCP server over stdio transport by default.")
            print("  Requires shared VDS environment configuration to be available.")
            return
        load_settings()
        mcp.run()


if __name__ == "__main__":
    main()
