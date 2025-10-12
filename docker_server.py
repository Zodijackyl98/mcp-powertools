"""
Docker MCP Server
Provides Docker management commands on the Raspberry Pi
Allows listing, inspecting, starting, stopping, and removing containers/images
Also supports running full docker compose commands such as:
docker compose -f ./docker-compose.yml up -d
"""

import asyncio
import subprocess
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

server = Server("docker-server")


@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="list_containers",
            description="List all Docker containers (running and stopped)",
            inputSchema={
                "type": "object",
                "properties": {
                    "all": {
                        "type": "boolean",
                        "description": "Show all containers (default: true)",
                        "default": True
                    }
                }
            }
        ),
        Tool(
            name="list_running_containers",
            description="List only running Docker containers",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="start_container",
            description="Start a stopped container",
            inputSchema={
                "type": "object",
                "properties": {
                    "container_id": {
                        "type": "string",
                        "description": "Container ID or name to start"
                    }
                },
                "required": ["container_id"]
            }
        ),
        Tool(
            name="stop_container",
            description="Stop a running container",
            inputSchema={
                "type": "object",
                "properties": {
                    "container_id": {
                        "type": "string",
                        "description": "Container ID or name to stop"
                    }
                },
                "required": ["container_id"]
            }
        ),
        Tool(
            name="remove_container",
            description="Remove a stopped container",
            inputSchema={
                "type": "object",
                "properties": {
                    "container_id": {
                        "type": "string",
                        "description": "Container ID or name to remove"
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Force remove container if running (default: false)",
                        "default": False
                    }
                },
                "required": ["container_id"]
            }
        ),
        Tool(
            name="list_images",
            description="List available Docker images",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="remove_image",
            description="Remove a Docker image by ID or name",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_id": {
                        "type": "string",
                        "description": "Image ID or name to remove"
                    }
                },
                "required": ["image_id"]
            }
        ),
        Tool(
            name="inspect_container",
            description="Inspect a container and return detailed information",
            inputSchema={
                "type": "object",
                "properties": {
                    "container_id": {
                        "type": "string",
                        "description": "Container ID or name to inspect"
                    }
                },
                "required": ["container_id"]
            }
        ),
        Tool(
            name="get_docker_info",
            description="Get system-wide Docker information (similar to `docker info`)",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="docker_compose",
            description="Run docker compose commands (e.g., `docker compose -f ./docker-compose.yml up -d`)",
            inputSchema={
                "type": "object",
                "properties": {
                    "args": {
                        "type": "array",
                        "description": "Full list of arguments for docker compose (e.g., ['-f', './file.yml', 'up', '-d'])",
                        "items": {"type": "string"}
                    },
                    "project_dir": {
                        "type": "string",
                        "description": "Directory containing docker-compose file (optional)",
                        "default": "."
                    }
                },
                "required": ["args"]
            }
        )
    ]


def run_docker_command(args: list[str], cwd: str = None) -> str:
    """Execute a Docker or Docker Compose command and return formatted output."""
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=cwd or None
        )
        if result.returncode == 0:
            return result.stdout.strip() or "Command executed successfully with no output."
        else:
            return f"Error (exit code {result.returncode}):\n{result.stderr.strip()}"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out after 120 seconds."
    except Exception as e:
        return f"Error executing command: {e}"


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "list_containers":
        all_flag = arguments.get("all", True)
        args = ["docker", "ps", "-a"] if all_flag else ["docker", "ps"]
        output = run_docker_command(args)
        return [TextContent(type="text", text=output)]

    elif name == "list_running_containers":
        output = run_docker_command(["docker", "ps"])
        return [TextContent(type="text", text=output)]

    elif name == "start_container":
        container_id = arguments["container_id"]
        output = run_docker_command(["docker", "start", container_id])
        return [TextContent(type="text", text=output)]

    elif name == "stop_container":
        container_id = arguments["container_id"]
        output = run_docker_command(["docker", "stop", container_id])
        return [TextContent(type="text", text=output)]

    elif name == "remove_container":
        container_id = arguments["container_id"]
        force = arguments.get("force", False)
        args = ["docker", "rm"]
        if force:
            args.append("-f")
        args.append(container_id)
        output = run_docker_command(args)
        return [TextContent(type="text", text=output)]

    elif name == "list_images":
        output = run_docker_command(["docker", "images"])
        return [TextContent(type="text", text=output)]

    elif name == "remove_image":
        image_id = arguments["image_id"]
        output = run_docker_command(["docker", "rmi", image_id])
        return [TextContent(type="text", text=output)]

    elif name == "inspect_container":
        container_id = arguments["container_id"]
        output = run_docker_command(["docker", "inspect", container_id])
        return [TextContent(type="text", text=output)]

    elif name == "get_docker_info":
        output = run_docker_command(["docker", "info"])
        return [TextContent(type="text", text=output)]

    elif name == "docker_compose":
        args = arguments["args"]
        project_dir = arguments.get("project_dir", ".")
        cmd = ["docker", "compose"] + args
        output = run_docker_command(cmd, cwd=project_dir)
        return [TextContent(type="text", text=output)]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    print("Docker MCP Server started. Managing local Docker environment.")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
