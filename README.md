# MCP Powertools

A collection of Model Context Protocol (MCP) servers that enable Large Language Models to interact with databases, filesystems, and system services.

## Overview

MCP Toolkit provides production-ready MCP servers that give LLMs the ability to perform real-world operations including database management, file manipulation, and system administration. Each server is designed with safety, security, and ease of use in mind.

## Features

- **Multi-Database Support**: Connect to multiple PostgreSQL instances simultaneously(script will be added for windows machines shortly)
- **Comprehensive Database Operations**: Making complex queries effortlessly
- **File System Management**: Complete file operations with path restrictions
- **Bash Script Automation**: Create and execute bash scripts
- **Safety Features**: Confirmation prompts for destructive operations
- **Tool Prefixing**: Unique tool names prevent confusion between multiple PostgreSQL servers running on different machines

## Available Servers

### PostgreSQL Server

Full-featured PostgreSQL database management with support for:

- Database creation/deletion
- Table creation with columns, constraints, and foreign keys
- Column management (add/drop columns)
- Index creation and management
- Query execution and optimization
- Statistics and analysis
- Multi-database connections

**Tool Prefix**: `pi_` for Raspberry Pi, `desktop_` for windows desktop installations

### Filesystem Server

Complete file system operations for Raspberry Pi or Linux systems:

- Read, write, append, and delete files
- Directory operations (create, list, delete)
- File search by pattern
- Copy and move operations
- Bash script creation and execution
- System information monitoring
- Network information

### Docker Server

Container and image management capabilities:

- Container lifecycle management
- Image operations
- Volume and network management
- Container logs and statistics
- Compose file operations

## Installation

### Prerequisites

- Python 3.8 or higher
- PostgreSQL (for database servers)
- Docker (for Docker server)
- SSH access (for remote servers)

### Install Dependencies

```bash
pip install mcp psycopg2-binary
```

### Server Setup

1. Clone the repository:
```bash
git clone https://github.com/Zodijackyl98/mcp-toolkit.git
cd mcp-toolkit
```

2. Configure your servers by creating .env file in the same folder and update it accordingly or  editing the connection parameters in each server file:

For PostgreSQL servers:
```python
BASE_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "your_username",
    "password": "your_password"
}
```

For Filesystem server:
```python
HOME_DIR = Path("/home/your_username")
```

3. Test the server:
```bash
python servers/postgresql/postgres_server.py
```

## Configuration

### SSH Setup for Remote Servers

For remote server access needed on applications such as LM Studio, set up SSH key authentication on the machine you run your model locally:

```bash
# Generate SSH key
ssh-keygen -t ed25519

# Copy to remote server
ssh-copy-id -p PORT user@host

# Test connection
ssh -p PORT user@host
```

### MCP Client Configuration

Example configuration for LM Studio or similar MCP clients, I use miniforge environment, put your own python executable location.:

```json
{
  "mcpServers": {
    "postgresql-pi": {
      "command": "ssh",
      "args": [
        "-p", "5427",
        "user@raspberrpi_ip",
        "/home/user/miniforge3/envs/your_mcp_environment/python3",
        "/path/to/postgres_server.py"
      ]
    },
    "filesystem": {
      "command": "ssh",
      "args": [
        "-p", "5427",
        "user@raspberrpi_ip",
        "/home/user/miniforge3/envs/your_mcp_environment/python3",
        "/path/to/pi_server.py"
      ]
    }
  }
}
```

## Usage Examples

### Create a Database

```
Create a new database called 'myapp' on the Raspberry Pi PostgreSQL server
```

The LLM will use the `pi_create_database` tool with appropriate parameters.

### Create a Table with Foreign Keys

```
Create a table called 'orders' with columns:
- id (serial primary key)
- user_id (integer, foreign key to users.id)
- total (decimal)
- created_at (timestamp, default now)
```

The LLM will use the `pi_create_table` tool with column definitions and foreign key constraints.

### File Operations

```
Create a Python script at /home/user/scripts/backup.py that backs up 
the database to /home/user/backups/
```

The LLM will use file creation and bash script tools to accomplish this.

## Security Considerations

### Database Servers

- **Read-Only Mode**: Set `READ_ONLY = True` to prevent write operations
- **Allowed Schemas**: Limit accessible schemas via `ALLOWED_SCHEMAS`
- **Row Limits**: Maximum rows per query set to 1000 by default
- **Confirmation Required**: Destructive operations require explicit confirmation

### Filesystem Server

- **Path Restrictions**: All operations restricted to specified base directory
- **Safe Commands**: Only whitelisted commands can be executed
- **No Root Access**: Server should run with limited user permissions

### General

- **SSH Key Authentication**: Use SSH keys instead of passwords
- **Network Isolation**: Run servers on isolated networks when possible
- **Audit Logging**: Monitor server logs for suspicious activity
- **Regular Updates**: Keep dependencies updated

## Tool Naming Convention

To prevent confusion when running multiple database servers, each server uses unique tool prefixes:

- Raspberry Pi PostgreSQL: `pi_` prefix (e.g., `pi_list_databases`)
- Desktop PostgreSQL: `desktop_` prefix (e.g., `desktop_list_databases`)
- Filesystem: Standard names (e.g., `read_file`, `write_file`)

This ensures the LLM always uses the correct server for each operation.

## Architecture

### Server Communication

MCP servers communicate via standard input/output (stdio), making them easy to integrate with any MCP-compatible client. For remote servers, SSH provides the transport layer.

```
[LLM Client] <-> [MCP Client] <-> [SSH] <-> [MCP Server] <-> [Database/System]
```

### Tool Execution Flow

1. LLM decides which tool to use based on user request and context that users need to provide
2. MCP client sends tool call with parameters
3. Server validates parameters and checks permissions
4. Server executes operation on target system
5. Server returns formatted results
6. LLM presents results to user

## Development

### Adding New Tools

To add a new tool to a server:

1. Define the tool in `list_tools()`:
```python
Tool(
    name="server_prefix_tool_name",
    description="Clear description of what the tool does",
    inputSchema={
        "type": "object",
        "properties": {
            "param_name": {
                "type": "string",
                "description": "Parameter description"
            }
        },
        "required": ["param_name"]
    }
)
```

2. Implement the tool in `call_tool()`:
```python
elif tool_name == "tool_name":
    # Implementation
    result = perform_operation(arguments)
    return [TextContent(type="text", text=result)]
```

## Troubleshooting

### Connection Issues

**Problem**: Server not responding
- Check if the server process is running
- Verify SSH connection: `ssh -p PORT user@host`
- Check firewall rules

**Problem**: Authentication failed
- Verify SSH keys are properly installed
- Check user permissions on remote server
- Confirm connection parameters in config

### Database Issues

**Problem**: Permission denied
- Verify database user has necessary privileges
- Check `ALLOWED_SCHEMAS` configuration
- Confirm database exists and is accessible

**Problem**: Query timeout
- Reduce result set size with LIMIT
- Optimize query with indexes
- Check `MAX_ROWS` setting

### Tool Issues

**Problem**: LLM uses wrong server
- Verify tool prefixes are unique
- Check MCP client configuration
- Restart LLM client to reload tools

## Acknowledgments

- Built on the Model Context Protocol by Anthropic
- Inspired by the need for safe, practical LLM-system integration
- I could not recommend more using [osmosis-ai](https://huggingface.co/osmosis-ai/osmosis-mcp-4b) which is very light but very powerful LLM tuned for MCPs. 

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing documentation
