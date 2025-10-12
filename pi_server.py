"""
Raspberry Pi MCP Server
Install this on your Raspberry Pi
Provides file operations and system commands
Full access to /home/mert
"""

import asyncio
import os
import subprocess
import shutil
from pathlib import Path
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, Resource, TextContent

server = Server("raspberry-pi-server")

# Configure safe directories - everything under /home/mert

HOME_DIR = Path("/home/mert")  #CHANGE THE USER !!!

def is_safe_path(path: str) -> tuple[bool, Path]:
    """Check if path is within /home/mert"""
    try:
        full_path = Path(path).resolve()
        # Allow anything under /home/mert
        if str(full_path).startswith(str(HOME_DIR.resolve())):
            return True, full_path
        return False, full_path
    except Exception:
        return False, None


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="read_file",
            description="Read contents of a file",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Full path to the file"
                    }
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="write_file",
            description="Write content to a file (creates parent directories if needed)",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Full path to the file"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write"
                    }
                },
                "required": ["path", "content"]
            }
        ),
        Tool(
            name="append_file",
            description="Append content to an existing file",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Full path to the file"
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to append"
                    }
                },
                "required": ["path", "content"]
            }
        ),
        Tool(
            name="list_directory",
            description="List contents of a directory",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to list"
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "List recursively (default: false)",
                        "default": False
                    }
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="create_directory",
            description="Create a new directory (creates parent directories automatically)",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to create"
                    }
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="delete_file",
            description="Delete a file",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path to delete"
                    }
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="delete_directory",
            description="Delete a directory and all its contents",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to delete"
                    }
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="move_file",
            description="Move or rename a file or directory",
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Source path"
                    },
                    "destination": {
                        "type": "string",
                        "description": "Destination path"
                    }
                },
                "required": ["source", "destination"]
            }
        ),
        Tool(
            name="copy_file",
            description="Copy a file or directory",
            inputSchema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Source path"
                    },
                    "destination": {
                        "type": "string",
                        "description": "Destination path"
                    }
                },
                "required": ["source", "destination"]
            }
        ),
        Tool(
            name="search_files",
            description="Search for files by name pattern",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory to search in"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "File name pattern (e.g., '*.txt', 'test*')"
                    }
                },
                "required": ["path", "pattern"]
            }
        ),
        Tool(
            name="get_file_info",
            description="Get detailed information about a file or directory",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to file or directory"
                    }
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="run_command",
            description="Execute a shell command (restricted to safe commands)",
            inputSchema={
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command to execute"
                    }
                },
                "required": ["command"]
            }
        ),
        Tool(
            name="get_system_info",
            description="Get system information",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_network_info",
            description="Get network interface information ",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),        
        Tool(
            name="create_bash_script",
            description="Create a bash script file with proper permissions",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Full path where to save the script (e.g., /home/mert/scripts/backup.sh)"
                    },
                    "content": {
                        "type": "string",
                        "description": "Bash script content (shebang will be added automatically if not present)"
                    },
                    "make_executable": {
                        "type": "boolean",
                        "description": "Make the script executable (default: true)",
                        "default": True
                    }
                },
                "required": ["path", "content"]
            }
        ),
        Tool(
            name="execute_bash_script",
            description="Execute a bash script file",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Full path to the bash script"
                    },
                    "args": {
                        "type": "array",
                        "description": "Arguments to pass to the script",
                        "items": {"type": "string"},
                        "default": []
                    }
                },
                "required": ["path"]
            }
        ),

    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    
    if name == "read_file":
        path = arguments["path"]
        is_safe, full_path = is_safe_path(path)
        
        if not is_safe:
            return [TextContent(
                type="text",
                text=f"Error: Access denied. Only paths under /home/mert are allowed."
            )]
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return [TextContent(
                type="text",
                text=f"File: {path}\n\n{content}"
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error reading file: {str(e)}"
            )]
    
    elif name == "write_file":
        path = arguments["path"]
        content = arguments["content"]
        is_safe, full_path = is_safe_path(path)
        
        if not is_safe:
            return [TextContent(
                type="text",
                text=f"Error: Access denied. Only paths under /home/mert are allowed."
            )]
        
        try:
            # Create parent directory if it doesn't exist
            full_path.parent.mkdir(parents=True, exist_ok=True)
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return [TextContent(
                type="text",
                text=f"Successfully wrote to {path}"
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error writing file: {str(e)}"
            )]
    
    elif name == "append_file":
        path = arguments["path"]
        content = arguments["content"]
        is_safe, full_path = is_safe_path(path)
        
        if not is_safe:
            return [TextContent(
                type="text",
                text=f"Error: Access denied. Only paths under /home/mert are allowed."
            )]
        
        try:
            with open(full_path, 'a', encoding='utf-8') as f:
                f.write(content)
            return [TextContent(
                type="text",
                text=f"Successfully appended to {path}"
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error appending to file: {str(e)}"
            )]
    
    elif name == "list_directory":
        path = arguments["path"]
        recursive = arguments.get("recursive", False)
        is_safe, full_path = is_safe_path(path)
        
        if not is_safe:
            return [TextContent(
                type="text",
                text=f"Error: Access denied. Only paths under /home/mert are allowed."
            )]
        
        try:
            if recursive:
                # Recursive listing
                all_items = []
                for root, dirs, files in os.walk(full_path):
                    level = root.replace(str(full_path), '').count(os.sep)
                    indent = ' ' * 2 * level
                    all_items.append(f"{indent}📁 {os.path.basename(root)}/")
                    subindent = ' ' * 2 * (level + 1)
                    for file in files:
                        all_items.append(f"{subindent}📄 {file}")
                listing = "\n".join(all_items)
            else:
                # Simple listing
                items = list(full_path.iterdir())
                files = [f"📄 {item.name}" for item in items if item.is_file()]
                dirs = [f"📁 {item.name}/" for item in items if item.is_dir()]
                listing = "\n".join(sorted(dirs) + sorted(files))
            
            return [TextContent(
                type="text",
                text=f"Contents of {path}:\n\n{listing}"
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error listing directory: {str(e)}"
            )]
    
    elif name == "create_directory":
        path = arguments["path"]
        is_safe, full_path = is_safe_path(path)
        
        if not is_safe:
            return [TextContent(
                type="text",
                text=f"Error: Access denied. Only paths under /home/mert are allowed."
            )]
        
        try:
            full_path.mkdir(parents=True, exist_ok=True)
            return [TextContent(
                type="text",
                text=f"Successfully created directory: {path}"
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error creating directory: {str(e)}"
            )]
    
    elif name == "delete_file":
        path = arguments["path"]
        is_safe, full_path = is_safe_path(path)
        
        if not is_safe:
            return [TextContent(
                type="text",
                text=f"Error: Access denied. Only paths under /home/mert are allowed."
            )]
        
        try:
            if full_path.is_file():
                full_path.unlink()
                return [TextContent(
                    type="text",
                    text=f"Successfully deleted: {path}"
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"Error: {path} is not a file"
                )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error deleting file: {str(e)}"
            )]
    
    elif name == "delete_directory":
        path = arguments["path"]
        is_safe, full_path = is_safe_path(path)

        if not is_safe:
            return [TextContent(
                type="text",
                text=f"Error: Access denied. Only paths under /home/mert are allowed."
            )]

        try:
            if full_path.is_dir():
                # Prevent deleting /home/mert itself
                if full_path == HOME_DIR:
                    return [TextContent(
                        type="text",
                        text=f"Error: Cannot delete the home directory itself"
                    )]

                shutil.rmtree(full_path)
                return [TextContent(
                    type="text",
                    text=f"Successfully deleted directory: {path}"
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"Error: {path} is not a directory"
                )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error deleting directory: {str(e)}"
            )]
    
    elif name == "move_file":
        source = arguments["source"]
        destination = arguments["destination"]
        
        is_safe_src, full_src = is_safe_path(source)
        is_safe_dst, full_dst = is_safe_path(destination)
        
        if not is_safe_src or not is_safe_dst:
            return [TextContent(
                type="text",
                text=f"Error: Access denied. Only paths under /home/mert are allowed."
            )]
        
        try:
            shutil.move(str(full_src), str(full_dst))
            return [TextContent(
                type="text",
                text=f"Successfully moved {source} to {destination}"
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error moving file: {str(e)}"
            )]
    
    elif name == "copy_file":
        source = arguments["source"]
        destination = arguments["destination"]
        
        is_safe_src, full_src = is_safe_path(source)
        is_safe_dst, full_dst = is_safe_path(destination)
        
        if not is_safe_src or not is_safe_dst:
            return [TextContent(
                type="text",
                text=f"Error: Access denied. Only paths under /home/mert are allowed."
            )]
        
        try:
            if full_src.is_file():
                shutil.copy2(str(full_src), str(full_dst))
            elif full_src.is_dir():
                shutil.copytree(str(full_src), str(full_dst))
            return [TextContent(
                type="text",
                text=f"Successfully copied {source} to {destination}"
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error copying file: {str(e)}"
            )]
    
    elif name == "search_files":
        path = arguments["path"]
        pattern = arguments["pattern"]
        is_safe, full_path = is_safe_path(path)
        
        if not is_safe:
            return [TextContent(
                type="text",
                text=f"Error: Access denied. Only paths under /home/mert are allowed."
            )]
        
        try:
            matches = list(full_path.rglob(pattern))
            if matches:
                results = "\n".join([f"📄 {m.relative_to(full_path)}" for m in matches])
                return [TextContent(
                    type="text",
                    text=f"Found {len(matches)} matches:\n\n{results}"
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"No files matching '{pattern}' found in {path}"
                )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error searching files: {str(e)}"
            )]
    
    elif name == "get_file_info":
        path = arguments["path"]
        is_safe, full_path = is_safe_path(path)
        
        if not is_safe:
            return [TextContent(
                type="text",
                text=f"Error: Access denied. Only paths under /home/mert are allowed."
            )]
        
        try:
            stat = full_path.stat()
            info = []
            info.append(f"Path: {path}")
            info.append(f"Type: {'Directory' if full_path.is_dir() else 'File'}")
            info.append(f"Size: {stat.st_size:,} bytes")
            info.append(f"Modified: {stat.st_mtime}")
            info.append(f"Permissions: {oct(stat.st_mode)[-3:]}")
            
            return [TextContent(
                type="text",
                text="\n".join(info)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error getting file info: {str(e)}"
            )]
    
    elif name == "run_command":
        command = arguments["command"]
        
        # Whitelist of safe commands
        safe_commands = [
            "ls", "pwd", "whoami", "date", "uptime", "df", "free",
            "cat", "grep", "find", "du", "wc", "systemctl status",
            "vcgencmd measure_temp"
        ]
        
        is_allowed = any(command.startswith(cmd) for cmd in safe_commands)
        
        if not is_allowed:
            return [TextContent(
                type="text",
                text=f"Error: Command '{command}' not allowed. Allowed: {', '.join(safe_commands)}"
            )]
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            output = f"Command: {command}\n\n"
            if result.stdout:
                output += f"Output:\n{result.stdout}\n"
            if result.stderr:
                output += f"Errors:\n{result.stderr}\n"
            output += f"\nReturn code: {result.returncode}"
            
            return [TextContent(type="text", text=output)]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error executing command: {str(e)}"
            )]
    
    elif name == "get_system_info":
        try:
            info = []
            
            # CPU temp (Pi-specific)
            try:
                temp_result = subprocess.run(
                    ["vcgencmd", "measure_temp"],
                    capture_output=True,
                    text=True
                )
                info.append(f"Temperature: {temp_result.stdout.strip()}")
            except:
                pass
            
            # Memory
            mem_result = subprocess.run(
                ["free", "-h"],
                capture_output=True,
                text=True
            )
            info.append(f"\nMemory:\n{mem_result.stdout}")
            
            # Disk
            disk_result = subprocess.run(
                ["df", "-h", "/"],
                capture_output=True,
                text=True
            )
            info.append(f"\nDisk:\n{disk_result.stdout}")
            
            # Uptime
            uptime_result = subprocess.run(
                ["uptime"],
                capture_output=True,
                text=True
            )
            info.append(f"\nUptime: {uptime_result.stdout.strip()}")
            
            return [TextContent(
                type="text",
                text="\n".join(info)
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error getting system info: {str(e)}"
            )]
    elif name == "get_network_info":
        try:
            # Execute 'ip addr' to get all network interfaces and IP addresses
            result = subprocess.run(
                ["ip", "addr"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return [TextContent(
                    type="text",
                    text=f"Network Information:\n\n{result.stdout}"
                )]
            else:
                return [TextContent(
                    type="text",
                    text=f"Error running 'ip addr -a':\n{result.stderr}"
                )]
        except subprocess.TimeoutExpired:
            return [TextContent(
                type="text",
                text="Error: 'ip addr -a' command timed out after 10 seconds"
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error retrieving network info: {str(e)}"
            )]    
    elif name == "create_bash_script":
        path = arguments["path"]
        content = arguments["content"]
        make_executable = arguments.get("make_executable", True)
        
        is_safe, full_path = is_safe_path(path)
        
        if not is_safe:
            return [TextContent(
                type="text",
                text=f"Error: Access denied. Only paths under /home/mert are allowed."
            )]
        
        try:
            # Add shebang if not present
            if not content.startswith("#!"):
                content = "#!/bin/bash\n\n" + content
            
            # Create parent directory if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write the script
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Make executable if requested
            if make_executable:
                os.chmod(full_path, 0o755)
                perm_msg = " (executable)"
            else:
                perm_msg = ""
            
            return [TextContent(
                type="text",
                text=f"Successfully created bash script at {path}{perm_msg}"
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error creating bash script: {str(e)}"
            )]
    
    elif name == "execute_bash_script":
        path = arguments["path"]
        script_args = arguments.get("args", [])
        
        is_safe, full_path = is_safe_path(path)
        
        if not is_safe:
            return [TextContent(
                type="text",
                text=f"Error: Access denied. Only paths under /home/mert are allowed."
            )]
        
        try:
            # Check if file exists
            if not full_path.exists():
                return [TextContent(
                    type="text",
                    text=f"Error: Script not found at {path}"
                )]
            
            # Check if file is executable
            if not os.access(full_path, os.X_OK):
                return [TextContent(
                    type="text",
                    text=f"Error: Script {path} is not executable. Run chmod +x on it first."
                )]
            
            # Execute the script
            result = subprocess.run(
                [str(full_path)] + script_args,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=full_path.parent
            )
            
            output = f"Executed: {path}\n"
            if script_args:
                output += f"Arguments: {' '.join(script_args)}\n"
            output += "\n"
            
            if result.stdout:
                output += f"Output:\n{result.stdout}\n"
            if result.stderr:
                output += f"Errors:\n{result.stderr}\n"
            output += f"\nExit code: {result.returncode}"
            
            return [TextContent(type="text", text=output)]
        except subprocess.TimeoutExpired:
            return [TextContent(
                type="text",
                text=f"Error: Script execution timed out after 60 seconds"
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"Error executing script: {str(e)}"
            )]


async def main():
    print("Raspberry Pi MCP Server started")
    print(f"Full access to: {HOME_DIR}")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())