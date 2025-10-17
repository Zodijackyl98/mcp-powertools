"""
CWEBP MCP Server
Convert images in a directory to WebP and search for image files
"""
import asyncio
import subprocess
import os
from pathlib import Path
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from dotenv import load_dotenv

load_dotenv()

server = Server("CWEBP")

# Configuration
DEFAULT_IMG_DIR = os.getenv("DEFAULT_IMG_DIR")
DEFAULT_OUTPUT_DIR = os.getenv("DEFAULT_OUTPUT_DIR")

@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="transform",
            description="Transform images in a directory into WebP format",
            inputSchema={
                "type": "object",
                "properties": {
                    "folder_destination": {
                        "type": "string",
                        "description": f"Source folder destination (default: {DEFAULT_IMG_DIR})",
                        "default": DEFAULT_IMG_DIR
                    },
                    "output_folder_destination": {
                        "type": "string",
                        "description": f"Output folder destination (default: {DEFAULT_OUTPUT_DIR})",
                        "default": DEFAULT_OUTPUT_DIR
                    },
                    "same": {
                        "type": "boolean",
                        "description": "Use the source folder as output folder as well (default: True)",
                        "default": True
                    }
                },
                "required": ["folder_destination", "output_folder_destination", "same"]
            }
        ),
        Tool(
            name="search_image",
            description="Find .png, .jpg, .jpeg images in a folder",
            inputSchema={
                "type": "object",
                "properties": {
                    "search_destination": {
                        "type": "string",
                        "description": "Folder to search for images"
                    }
                },
                "required": ["search_destination"]
            }
        )
    ]

def convert_images_to_webp(src_folder: str, out_folder: str) -> str:
    src = Path(src_folder)
    out = Path(out_folder)
    out.mkdir(parents=True, exist_ok=True)

    results = []
    for img in src.glob("*.[pj][pn]g"):
        output_path = out / (img.stem + ".webp")
        cmd = ["cwebp", str(img), "-o", str(output_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        results.append(f"{img.name} → {output_path.name} [{result.returncode}]")
    return "\n".join(results) or "No images found."

@server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "transform":
        folder_input = arguments["folder_destination"]
        folder_output = arguments["output_folder_destination"]
        same = arguments["same"]

        if same:
            folder_output = folder_input

        output = convert_images_to_webp(folder_input, folder_output)
        return [TextContent(type="text", text=output)]

    elif name == "search_image":
        folder = arguments["search_destination"]
        cmd = f'find "{folder}" -type f \\( -iname "*.jpg" -o -iname "*.jpeg" -o -iname "*.png" \\ )'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return [TextContent(type="text", text=result.stdout or "No images found.")]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    print("CWEBP Server Has Started")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
