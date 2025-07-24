"""Allow running the package as a module with python -m chromadb_mcp_server."""

from .main import cli_main

if __name__ == "__main__":
    cli_main()