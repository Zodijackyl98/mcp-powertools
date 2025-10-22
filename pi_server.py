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
import json
import signal
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


# ============================================
# PROCESS MONITORING FUNCTIONS
# ============================================

def parse_top_output() -> list[dict]:
    """Parse 'top' command output and return process information"""
    try:
        # Run top in batch mode for 1 iteration
        result = subprocess.run(
            ["top", "-b", "-n", "1"],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        processes = []
        lines = result.stdout.split('\n')
        
        # Find the header line
        header_idx = 0
        for i, line in enumerate(lines):
            if 'PID' in line and 'USER' in line:
                header_idx = i
                break
        
        # Parse process lines
        for line in lines[header_idx + 1:]:
            if not line.strip():
                continue
            
            parts = line.split()
            if len(parts) < 12:
                continue
            
            try:
                pid = int(parts[0])
                user = parts[1]
                cpu = float(parts[8])
                mem = float(parts[9])
                command = ' '.join(parts[11:])
                
                # Get full path of executable
                try:
                    exe_path = os.readlink(f"/proc/{pid}/exe")
                except:
                    exe_path = "N/A"
                
                # Get process UUID (using inode as unique identifier)
                try:
                    stat_info = os.stat(f"/proc/{pid}")
                    uuid = f"{pid}-{stat_info.st_ino}"
                except:
                    uuid = f"{pid}-unknown"
                
                processes.append({
                    "pid": pid,
                    "user": user,
                    "cpu_percent": cpu,
                    "mem_percent": mem,
                    "command": command,
                    "executable_path": exe_path,
                    "uuid": uuid
                })
            except (ValueError, IndexError):
                continue
        
        return processes
    except Exception as e:
        return [{"error": f"Failed to parse top output: {str(e)}"}]


def parse_glances_output() -> dict:
    """Parse 'glances' command output and return detailed system info"""
    try:
        # Run glances in export json mode
        result = subprocess.run(
            ["glances", "-w", "--export", "json"],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.returncode != 0:
            # Fallback: use glances without web mode
            result = subprocess.run(
                ["glances", "--export", "json"],
                capture_output=True,
                text=True,
                timeout=15
            )
        
        # Try to parse JSON output
        try:
            data = json.loads(result.stdout)
            return data
        except json.JSONDecodeError:
            return {"raw_output": result.stdout, "error": "Could not parse JSON"}
    except FileNotFoundError:
        return {"error": "glances not installed. Install with: sudo apt install glances"}
    except Exception as e:
        return {"error": f"Failed to run glances: {str(e)}"}


def get_process_by_name(name: str) -> list[dict]:
    """Get all processes matching a name pattern"""
    try:
        result = subprocess.run(
            ["pgrep", "-a", name],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        processes = []
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            
            parts = line.split(None, 1)
            pid = int(parts[0])
            command = parts[1] if len(parts) > 1 else "unknown"
            
            try:
                exe_path = os.readlink(f"/proc/{pid}/exe")
            except:
                exe_path = "N/A"
            
            try:
                stat_info = os.stat(f"/proc/{pid}")
                uuid = f"{pid}-{stat_info.st_ino}"
            except:
                uuid = f"{pid}-unknown"
            
            processes.append({
                "pid": pid,
                "command": command,
                "executable_path": exe_path,
                "uuid": uuid
            })
        
        return processes
    except Exception as e:
        return [{"error": f"Failed to search for process: {str(e)}"}]


def get_process_details(pid: int) -> dict:
    """Get detailed information about a specific process"""
    try:
        # Read process info
        with open(f"/proc/{pid}/stat", 'r') as f:
            stat_data = f.read().split()
        
        with open(f"/proc/{pid}/status", 'r') as f:
            status_data = f.read()
        
        # Get executable path
        try:
            exe_path = os.readlink(f"/proc/{pid}/exe")
        except:
            exe_path = "N/A"
        
        # Get command line
        try:
            with open(f"/proc/{pid}/cmdline", 'r') as f:
                cmdline = f.read().replace('\x00', ' ')
        except:
            cmdline = "N/A"
        
        # Parse status
        status_dict = {}
        for line in status_data.split('\n'):
            if ':' in line:
                key, value = line.split(':', 1)
                status_dict[key.strip()] = value.strip()
        
        # Get UUID
        try:
            stat_info = os.stat(f"/proc/{pid}")
            uuid = f"{pid}-{stat_info.st_ino}"
        except:
            uuid = f"{pid}-unknown"
        
        return {
            "pid": pid,
            "name": status_dict.get('Name', 'N/A'),
            "state": status_dict.get('State', 'N/A'),
            "ppid": status_dict.get('PPid', 'N/A'),
            "vm_rss": status_dict.get('VmRSS', 'N/A'),
            "vm_size": status_dict.get('VmSize', 'N/A'),
            "executable_path": exe_path,
            "command_line": cmdline,
            "uuid": uuid
        }
    except FileNotFoundError:
        return {"error": f"Process {pid} not found"}
    except Exception as e:
        return {"error": f"Failed to get process details: {str(e)}"}


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
        # Process Monitoring Tools
        Tool(
            name="list_all_processes",
            description="List all running processes with CPU, memory usage, paths, and UUIDs",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_top_processes",
            description="Get top N processes by CPU and memory usage",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of top processes to show (default: 10)",
                        "default": 10
                    }
                }
            }
        ),
        Tool(
            name="find_process_by_name",
            description="Search for processes by name",
            inputSchema={
                "type": "object",
                "properties": {
                    "process_name": {
                        "type": "string",
                        "description": "Name or pattern to search for"
                    }
                },
                "required": ["process_name"]
            }
        ),
        Tool(
            name="get_process_info",
            description="Get detailed information about a specific process",
            inputSchema={
                "type": "object",
                "properties": {
                    "pid": {
                        "type": "integer",
                        "description": "Process ID"
                    }
                },
                "required": ["pid"]
            }
        ),
        Tool(
            name="get_system_overview",
            description="Get system overview using glances (if available)",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="terminate_process",
            description="Terminate a process by PID",
            inputSchema={
                "type": "object",
                "properties": {
                    "pid": {
                        "type": "integer",
                        "description": "Process ID to terminate"
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Force kill (SIGKILL) instead of graceful (SIGTERM)",
                        "default": False
                    }
                },
                "required": ["pid"]
            }
        ),
        Tool(
            name="terminate_process_by_name",
            description="Terminate all processes matching a name",
            inputSchema={
                "type": "object",
                "properties": {
                    "process_name": {
                        "type": "string",
                        "description": "Name pattern to match"
                    },
                    "force": {
                        "type": "boolean",
                        "description": "Force kill (SIGKILL) instead of graceful (SIGTERM)",
                        "default": False
                    }
                },
                "required": ["process_name"]
            }
        ),
        Tool(
            name="get_process_tree",
            description="Get process tree starting from a parent PID",
            inputSchema={
                "type": "object",
                "properties": {
                    "parent_pid": {
                        "type": "integer",
                        "description": "Parent PID to start from (default: 1)",
                        "default": 1
                    }
                }
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
    
    # Process Monitoring Tools
    elif name == "list_all_processes":
        processes = parse_top_output()
        
        if not processes:
            return [TextContent(type="text", text="No processes found")]
        
        output = "Running Processes\n"
        output += "=" * 100 + "\n"
        output += f"{'PID':<8} {'USER':<10} {'CPU%':<8} {'MEM%':<8} {'Command':<30} {'Path':<30}\n"
        output += "-" * 100 + "\n"
        
        for proc in processes[:50]:  # Limit to first 50
            if "error" in proc:
                continue
            output += f"{proc['pid']:<8} {proc['user']:<10} {proc['cpu_percent']:<8.1f} "
            output += f"{proc['mem_percent']:<8.1f} {proc['command'][:30]:<30} "
            output += f"{proc['executable_path'][:30]:<30}\n"
        
        output += "\n\nUUID Reference:\n"
        for proc in processes[:50]:
            if "error" not in proc:
                output += f"PID {proc['pid']}: UUID {proc['uuid']}\n"
        
        return [TextContent(type="text", text=output)]
    
    elif name == "get_top_processes":
        limit = arguments.get("limit", 10)
        processes = parse_top_output()
        
        if not processes or "error" in processes[0]:
            return [TextContent(type="text", text="Failed to get process list")]
        
        # Sort by memory usage
        sorted_procs = sorted(processes, key=lambda x: x['mem_percent'], reverse=True)[:limit]
        
        output = f"Top {limit} Processes by Memory Usage\n"
        output += "=" * 100 + "\n"
        output += f"{'PID':<8} {'USER':<10} {'CPU%':<8} {'MEM%':<8} {'Command':<30} {'UUID':<20}\n"
        output += "-" * 100 + "\n"
        
        for proc in sorted_procs:
            output += f"{proc['pid']:<8} {proc['user']:<10} {proc['cpu_percent']:<8.1f} "
            output += f"{proc['mem_percent']:<8.1f} {proc['command'][:30]:<30} {proc['uuid']:<20}\n"
        
        return [TextContent(type="text", text=output)]
    
    elif name == "find_process_by_name":
        process_name = arguments["process_name"]
        processes = get_process_by_name(process_name)
        
        if not processes or "error" in processes[0]:
            return [TextContent(type="text", text=f"No processes found matching '{process_name}'")]
        
        output = f"Processes matching '{process_name}'\n"
        output += "=" * 80 + "\n"
        output += f"{'PID':<8} {'Command':<40} {'Path':<20}\n"
        output += "-" * 80 + "\n"
        
        for proc in processes:
            if "error" not in proc:
                output += f"{proc['pid']:<8} {proc['command'][:40]:<40} "
                output += f"{proc['executable_path'][:20]:<20}\n"
                output += f"  UUID: {proc['uuid']}\n"
        
        return [TextContent(type="text", text=output)]
    
    elif name == "get_process_info":
        pid = arguments["pid"]
        details = get_process_details(pid)
        
        if "error" in details:
            return [TextContent(type="text", text=details["error"])]
        
        output = f"Process Details (PID: {pid})\n"
        output += "=" * 60 + "\n"
        output += f"Name: {details['name']}\n"
        output += f"State: {details['state']}\n"
        output += f"Parent PID: {details['ppid']}\n"
        output += f"Memory (RSS): {details['vm_rss']}\n"
        output += f"Memory (Total): {details['vm_size']}\n"
        output += f"Executable Path: {details['executable_path']}\n"
        output += f"Command Line: {details['command_line']}\n"
        output += f"UUID: {details['uuid']}\n"
        
        return [TextContent(type="text", text=output)]
    
    elif name == "get_system_overview":
        glances_data = parse_glances_output()
        
        if "error" in glances_data:
            return [TextContent(type="text", text=f"Glances Error: {glances_data['error']}")]
        
        output = "System Overview (Glances)\n"
        output += "=" * 60 + "\n"
        
        # Try to extract key metrics
        if "cpu" in glances_data:
            output += f"CPU: {glances_data['cpu']}\n"
        
        if "mem" in glances_data:
            output += f"Memory: {glances_data['mem']}\n"
        
        if "swap" in glances_data:
            output += f"Swap: {glances_data['swap']}\n"
        
        if "fs" in glances_data:
            output += f"\nFile Systems: {len(glances_data['fs'])} mounted\n"
        
        if "processlist" in glances_data:
            output += f"Total Processes: {len(glances_data['processlist'])}\n"
        
        output += f"\nRaw data keys: {list(glances_data.keys())}\n"
        
        return [TextContent(type="text", text=output)]
    
    elif name == "terminate_process":
        pid = arguments["pid"]
        force = arguments.get("force", False)
        
        try:
            # Verify process exists
            details = get_process_details(pid)
            if "error" in details:
                return [TextContent(type="text", text=f"Error: Process {pid} not found")]
            
            signal_type = signal.SIGKILL if force else signal.SIGTERM
            signal_name = "SIGKILL (force)" if force else "SIGTERM"
            
            os.kill(pid, signal_type)
            
            return [TextContent(type="text", text=f"Successfully sent {signal_name} to process {pid} ({details['name']})")]
        except PermissionError:
            return [TextContent(type="text", text=f"Error: Permission denied. You may need sudo to terminate this process.")]
        except ProcessLookupError:
            return [TextContent(type="text", text=f"Error: Process {pid} not found or already terminated")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error terminating process: {str(e)}")]
    
    elif name == "terminate_process_by_name":
        process_name = arguments["process_name"]
        force = arguments.get("force", False)
        processes = get_process_by_name(process_name)
        
        if not processes or "error" in processes[0]:
            return [TextContent(type="text", text=f"No processes found matching '{process_name}'")]
        
        terminated = []
        failed = []
        
        for proc in processes:
            if "error" in proc:
                continue
            
            try:
                signal_type = signal.SIGKILL if force else signal.SIGTERM
                os.kill(proc['pid'], signal_type)
                terminated.append(proc['pid'])
            except Exception as e:
                failed.append((proc['pid'], str(e)))
        
        output = f"Terminated {len(terminated)} process(es) matching '{process_name}'\n"
        if terminated:
            output += f"Terminated PIDs: {', '.join(map(str, terminated))}\n"
        if failed:
            output += f"Failed to terminate: {failed}\n"
        
        return [TextContent(type="text", text=output)]
    
    elif name == "get_process_tree":
        parent_pid = arguments.get("parent_pid", 1)
        
        try:
            result = subprocess.run(
                ["pstree", "-p", str(parent_pid)],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                return [TextContent(type="text", text=f"Process Tree (starting from PID {parent_pid})\n" + result.stdout)]
            else:
                return [TextContent(type="text", text=f"pstree not available or PID {parent_pid} not found")]
        except FileNotFoundError:
            return [TextContent(type="text", text="pstree command not found. Install with: sudo apt install psmisc")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error getting process tree: {str(e)}")]

    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]


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