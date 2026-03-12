"""Template for registering MCP tools for a new service.

Copy this directory and rename to create a new tool module.
Replace 'example' with your service name throughout.
"""

from shared.server import ToolServer
from shared.types import ToolResult


def register(server: ToolServer) -> None:
    """Register all tools for this module with the MCP server."""
    server.register_tool(
        name="example_action",
        description="Description of what this tool does",
        input_schema={
            "type": "object",
            "properties": {
                "param": {"type": "string", "description": "Parameter description"},
            },
            "required": ["param"],
        },
        handler=handle_action,
    )


def handle_action(*, param: str) -> ToolResult:
    """Handle the example action."""
    return ToolResult(success=True, data={"result": f"Processed: {param}"})
