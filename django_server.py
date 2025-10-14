"""
Django MCP Server
Manage Django applications, run server, collect static, modify settings
"""
import asyncio
import subprocess
import os
import signal
import psutil
from pathlib import Path
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from dotenv import load_dotenv

load_dotenv()

server = Server("django-server")

# Configuration
DJANGO_PROJECT_PATH = Path(os.getenv('DJANGO_MAIN'))
MANAGE_PY = DJANGO_PROJECT_PATH / 'manage.py'
SETTINGS_PY = DJANGO_PROJECT_PATH / 'aft_django' / 'settings.py'
PYTHON_PATH = Path(os.getenv('DJANGO_PYTHON'))
DEFAULT_HOST = '192.168.1.35'
DEFAULT_PORT = '8000'

# Track running server process
running_server_pid = None

print("="*60)
print("DJANGO MCP SERVER")
print(f"Project: {DJANGO_PROJECT_PATH}")
print(f"Manage.py: {MANAGE_PY}")
print(f"Settings: {SETTINGS_PY}")
print("="*60)


def run_django_command(args: list[str], detach: bool = False, timeout: int = 120) -> dict:
    """Execute a Django management command."""
    try:
        command = [str(PYTHON_PATH), str(MANAGE_PY)] + args
        
        if detach:
            # Run in background (for runserver)
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(DJANGO_PROJECT_PATH)
            )
            return {
                "success": True,
                "output": f"Command started in background (PID: {process.pid})",
                "pid": process.pid
            }
        else:
            # Run synchronously
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(DJANGO_PROJECT_PATH)
            )
            
            if result.returncode == 0:
                return {
                    "success": True,
                    "output": result.stdout.strip() or "Command executed successfully",
                    "error": result.stderr.strip() if result.stderr else None
                }
            else:
                return {
                    "success": False,
                    "output": result.stdout.strip(),
                    "error": result.stderr.strip(),
                    "exit_code": result.returncode
                }
    
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Command timed out after {timeout} seconds"}
    except Exception as e:
        return {"success": False, "error": f"Error executing command: {str(e)}"}


def find_django_server_process():
    """Find running Django development server process."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and 'manage.py' in ' '.join(cmdline) and 'runserver' in ' '.join(cmdline):
                return proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None


@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="django_start_server",
            description="Start Django development server",
            inputSchema={
                "type": "object",
                "properties": {
                    "host": {
                        "type": "string",
                        "description": f"IP address (default: {DEFAULT_HOST})",
                        "default": DEFAULT_HOST
                    },
                    "port": {
                        "type": "string",
                        "description": f"Port (default: {DEFAULT_PORT})",
                        "default": DEFAULT_PORT
                    },
                    "noreload": {
                        "type": "boolean",
                        "description": "Disable auto-reloader (default: false)",
                        "default": False
                    }
                }
            }
        ),
        Tool(
            name="django_stop_server",
            description="Stop running Django development server",
            inputSchema={
                "type": "object",
                "properties": {
                    "force": {
                        "type": "boolean",
                        "description": "Force kill if graceful shutdown fails",
                        "default": False
                    }
                }
            }
        ),
        Tool(
            name="django_server_status",
            description="Check if Django server is running",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="django_collectstatic",
            description="Collect static files for Django project",
            inputSchema={
                "type": "object",
                "properties": {
                    "noinput": {
                        "type": "boolean",
                        "description": "Skip user prompts (default: true)",
                        "default": True
                    },
                    "clear": {
                        "type": "boolean",
                        "description": "Clear existing static files first",
                        "default": False
                    }
                }
            }
        ),
        Tool(
            name="django_makemigrations",
            description="Create new database migrations",
            inputSchema={
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Specific app to create migrations for (optional)"
                    },
                    "name": {
                        "type": "string",
                        "description": "Custom migration name (optional)"
                    }
                }
            }
        ),
        Tool(
            name="django_migrate",
            description="Apply database migrations",
            inputSchema={
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Specific app to migrate (optional)"
                    },
                    "fake": {
                        "type": "boolean",
                        "description": "Mark migrations as run without actually running them",
                        "default": False
                    }
                }
            }
        ),
        Tool(
            name="django_showmigrations",
            description="Show all migrations and their status",
            inputSchema={
                "type": "object",
                "properties": {
                    "app_name": {
                        "type": "string",
                        "description": "Filter by specific app (optional)"
                    }
                }
            }
        ),
        Tool(
            name="django_check",
            description="Check Django project for common issues",
            inputSchema={
                "type": "object",
                "properties": {
                    "deploy": {
                        "type": "boolean",
                        "description": "Check deployment settings",
                        "default": False
                    }
                }
            }
        ),
        Tool(
            name="django_get_setting",
            description="Get value of a Django setting",
            inputSchema={
                "type": "object",
                "properties": {
                    "setting_name": {
                        "type": "string",
                        "description": "Name of the setting (e.g., DEBUG, ALLOWED_HOSTS)"
                    }
                },
                "required": ["setting_name"]
            }
        ),
        Tool(
            name="django_update_setting",
            description="Update a Django setting in settings.py",
            inputSchema={
                "type": "object",
                "properties": {
                    "setting_name": {
                        "type": "string",
                        "description": "Name of the setting (e.g., DEBUG, ALLOWED_HOSTS)"
                    },
                    "setting_value": {
                        "type": "string",
                        "description": "New value (as Python code, e.g., 'True', '\"value\"', '[1, 2, 3]')"
                    },
                    "backup": {
                        "type": "boolean",
                        "description": "Create backup before modifying (default: true)",
                        "default": True
                    }
                },
                "required": ["setting_name", "setting_value"]
            }
        ),
        Tool(
            name="django_shell_command",
            description="Execute Python code in Django shell context",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code to execute"
                    }
                },
                "required": ["code"]
            }
        ),
        Tool(
            name="django_list_apps",
            description="List all installed Django apps",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="django_createsuperuser",
            description="Create Django superuser account",
            inputSchema={
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "Username for superuser"
                    },
                    "email": {
                        "type": "string",
                        "description": "Email for superuser"
                    },
                    "noinput": {
                        "type": "boolean",
                        "description": "Skip password prompt (password must be set later)",
                        "default": False
                    }
                },
                "required": ["username", "email"]
            }
        ),
        Tool(
            name="django_clear_cache",
            description="Clear Django cache",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="django_run_tests",
            description="Run Django tests",
            inputSchema={
                "type": "object",
                "properties": {
                    "app_or_test": {
                        "type": "string",
                        "description": "Specific app or test to run (optional)"
                    },
                    "keepdb": {
                        "type": "boolean",
                        "description": "Preserve test database",
                        "default": False
                    }
                }
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    global running_server_pid
    
    if name == "django_start_server":
        host = arguments.get("host", DEFAULT_HOST)
        port = arguments.get("port", DEFAULT_PORT)
        noreload = arguments.get("noreload", False)
        
        # Check if server already running
        existing_pid = find_django_server_process()
        if existing_pid:
            return [TextContent(
                type="text",
                text=f"[DJANGO] Server already running (PID: {existing_pid})\nUse django_stop_server to stop it first."
            )]
        
        args = ["runserver", f"{host}:{port}"]
        if noreload:
            args.append("--noreload")
        
        result = run_django_command(args, detach=True)
        
        if result["success"]:
            running_server_pid = result["pid"]
            output = f"[DJANGO] Development server started\n"
            output += f"PID: {result['pid']}\n"
            output += f"Address: http://{host}:{port}/\n"
            output += f"Auto-reload: {'Disabled' if noreload else 'Enabled'}"
        else:
            output = f"[DJANGO] Failed to start server\nError: {result.get('error', 'Unknown error')}"
        
        return [TextContent(type="text", text=output)]
    
    elif name == "django_stop_server":
        force = arguments.get("force", False)
        
        pid = find_django_server_process()
        if not pid:
            return [TextContent(type="text", text="[DJANGO] No running Django server found")]
        
        try:
            process = psutil.Process(pid)
            
            if force:
                process.kill()
                message = f"[DJANGO] Server forcefully stopped (PID: {pid})"
            else:
                process.terminate()
                try:
                    process.wait(timeout=5)
                    message = f"[DJANGO] Server stopped gracefully (PID: {pid})"
                except psutil.TimeoutExpired:
                    process.kill()
                    message = f"[DJANGO] Server killed after timeout (PID: {pid})"
            
            running_server_pid = None
            return [TextContent(type="text", text=message)]
        
        except Exception as e:
            return [TextContent(type="text", text=f"[DJANGO] Error stopping server: {str(e)}")]
    
    elif name == "django_server_status":
        pid = find_django_server_process()
        
        if pid:
            try:
                process = psutil.Process(pid)
                cmdline = ' '.join(process.cmdline())
                
                output = f"[DJANGO] Server Status: RUNNING\n"
                output += f"PID: {pid}\n"
                output += f"Command: {cmdline}\n"
                output += f"CPU: {process.cpu_percent()}%\n"
                output += f"Memory: {process.memory_info().rss / 1024 / 1024:.1f} MB"
            except:
                output = "[DJANGO] Server process found but couldn't get details"
        else:
            output = "[DJANGO] Server Status: NOT RUNNING"
        
        return [TextContent(type="text", text=output)]
    
    elif name == "django_collectstatic":
        noinput = arguments.get("noinput", True)
        clear = arguments.get("clear", False)
        
        args = ["collectstatic"]
        if noinput:
            args.append("--noinput")
        if clear:
            args.append("--clear")
        
        result = run_django_command(args, timeout=300)
        
        if result["success"]:
            output = f"[DJANGO] Static files collected successfully\n\n{result['output']}"
        else:
            output = f"[DJANGO] Error collecting static files\n{result.get('error', 'Unknown error')}"
        
        return [TextContent(type="text", text=output)]
    
    elif name == "django_makemigrations":
        app_name = arguments.get("app_name")
        migration_name = arguments.get("name")
        
        args = ["makemigrations"]
        if app_name:
            args.append(app_name)
        if migration_name:
            args.extend(["--name", migration_name])
        
        result = run_django_command(args)
        
        if result["success"]:
            output = f"[DJANGO] Migrations created\n\n{result['output']}"
        else:
            output = f"[DJANGO] Error creating migrations\n{result.get('error', 'Unknown error')}"
        
        return [TextContent(type="text", text=output)]
    
    elif name == "django_migrate":
        app_name = arguments.get("app_name")
        fake = arguments.get("fake", False)
        
        args = ["migrate"]
        if app_name:
            args.append(app_name)
        if fake:
            args.append("--fake")
        
        result = run_django_command(args, timeout=300)
        
        if result["success"]:
            output = f"[DJANGO] Migrations applied\n\n{result['output']}"
        else:
            output = f"[DJANGO] Error applying migrations\n{result.get('error', 'Unknown error')}"
        
        return [TextContent(type="text", text=output)]
    
    elif name == "django_showmigrations":
        app_name = arguments.get("app_name")
        
        args = ["showmigrations"]
        if app_name:
            args.append(app_name)
        
        result = run_django_command(args)
        
        if result["success"]:
            output = f"[DJANGO] Migration Status\n\n{result['output']}"
        else:
            output = f"[DJANGO] Error showing migrations\n{result.get('error', 'Unknown error')}"
        
        return [TextContent(type="text", text=output)]
    
    elif name == "django_check":
        deploy = arguments.get("deploy", False)
        
        args = ["check"]
        if deploy:
            args.append("--deploy")
        
        result = run_django_command(args)
        
        if result["success"]:
            output = f"[DJANGO] System Check\n\n{result['output']}"
        else:
            output = f"[DJANGO] System check found issues\n{result.get('error', result.get('output', 'Unknown error'))}"
        
        return [TextContent(type="text", text=output)]
    
    elif name == "django_get_setting":
        setting_name = arguments["setting_name"]
        
        try:
            with open(SETTINGS_PY, 'r') as f:
                content = f.read()
            
            # Simple regex to find setting
            import re
            pattern = rf'^{setting_name}\s*=\s*(.+)$'
            match = re.search(pattern, content, re.MULTILINE)
            
            if match:
                value = match.group(1).strip()
                output = f"[DJANGO] Setting: {setting_name}\nValue: {value}"
            else:
                output = f"[DJANGO] Setting '{setting_name}' not found in settings.py"
        
        except Exception as e:
            output = f"[DJANGO] Error reading settings: {str(e)}"
        
        return [TextContent(type="text", text=output)]
    
    elif name == "django_update_setting":
        setting_name = arguments["setting_name"]
        setting_value = arguments["setting_value"]
        backup = arguments.get("backup", True)
        
        try:
            # Create backup
            if backup:
                backup_path = SETTINGS_PY.with_suffix('.py.backup')
                with open(SETTINGS_PY, 'r') as f:
                    backup_content = f.read()
                with open(backup_path, 'w') as f:
                    f.write(backup_content)
            
            # Read current settings
            with open(SETTINGS_PY, 'r') as f:
                content = f.read()
            
            # Update setting
            import re
            pattern = rf'^({setting_name}\s*=\s*)(.+)$'
            
            def replace_setting(match):
                return f"{match.group(1)}{setting_value}"
            
            new_content, count = re.subn(pattern, replace_setting, content, flags=re.MULTILINE)
            
            if count == 0:
                # Setting doesn't exist, add it
                new_content += f"\n\n# Added by MCP\n{setting_name} = {setting_value}\n"
                action = "added"
            else:
                action = "updated"
            
            # Write back
            with open(SETTINGS_PY, 'w') as f:
                f.write(new_content)
            
            output = f"[DJANGO] Setting '{setting_name}' {action}\n"
            output += f"New value: {setting_value}\n"
            if backup:
                output += f"Backup saved to: {backup_path}"
        
        except Exception as e:
            output = f"[DJANGO] Error updating setting: {str(e)}"
        
        return [TextContent(type="text", text=output)]
    
    elif name == "django_shell_command":
        code = arguments["code"]
        
        # Create temporary script
        script_content = f"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aft_django.settings')
django.setup()

{code}
"""
        
        temp_script = DJANGO_PROJECT_PATH / '.mcp_temp_script.py'
        try:
            with open(temp_script, 'w') as f:
                f.write(script_content)
            
            result = subprocess.run(
                [str(PYTHON_PATH), str(temp_script)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(DJANGO_PROJECT_PATH)
            )
            
            if result.returncode == 0:
                output = f"[DJANGO] Shell command executed\n\n{result.stdout}"
            else:
                output = f"[DJANGO] Shell command failed\n{result.stderr}"
        
        except Exception as e:
            output = f"[DJANGO] Error executing shell command: {str(e)}"
        finally:
            if temp_script.exists():
                temp_script.unlink()
        
        return [TextContent(type="text", text=output)]
    
    elif name == "django_list_apps":
        code = """
from django.apps import apps
for app in apps.get_app_configs():
    print(f"{app.label}: {app.verbose_name}")
"""
        
        return await call_tool("django_shell_command", {"code": code})
    
    elif name == "django_createsuperuser":
        username = arguments["username"]
        email = arguments["email"]
        noinput = arguments.get("noinput", False)
        
        args = ["createsuperuser", "--username", username, "--email", email]
        if noinput:
            args.append("--noinput")
        
        result = run_django_command(args)
        
        if result["success"]:
            output = f"[DJANGO] Superuser created\n\n{result['output']}"
            if noinput:
                output += "\n\nNote: Password must be set using 'python manage.py changepassword {username}'"
        else:
            output = f"[DJANGO] Error creating superuser\n{result.get('error', 'Unknown error')}"
        
        return [TextContent(type="text", text=output)]
    
    elif name == "django_clear_cache":
        # Try to clear cache programmatically
        code = """
from django.core.cache import cache
cache.clear()
print("Cache cleared successfully")
"""
        
        return await call_tool("django_shell_command", {"code": code})
    
    elif name == "django_run_tests":
        app_or_test = arguments.get("app_or_test")
        keepdb = arguments.get("keepdb", False)
        
        args = ["test"]
        if app_or_test:
            args.append(app_or_test)
        if keepdb:
            args.append("--keepdb")
        
        result = run_django_command(args, timeout=600)
        
        if result["success"]:
            output = f"[DJANGO] Tests completed\n\n{result['output']}"
        else:
            output = f"[DJANGO] Tests failed or had errors\n{result.get('error', result.get('output', 'Unknown error'))}"
        
        return [TextContent(type="text", text=output)]
    
    else:
        return [TextContent(type="text", text=f"[DJANGO] Unknown tool: {name}")]


async def main():
    print("Django MCP Server started")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())