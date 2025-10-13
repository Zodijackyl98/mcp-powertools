"""
PostgreSQL MCP Server - DESKTOP DATABASE at localhost
Complete implementation with DDL operations
"""

import asyncio
import json
from typing import Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, Resource, TextContent

server = Server("postgresql-DESKTOP")

# DESKTOP DATABASE - runs on Windows
BASE_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "user": "mert",
    "password": "pulsar"
}

DEFAULT_DATABASE = "afterburner"
MAX_ROWS = 1000
ALLOWED_SCHEMAS = ["public"]
READ_ONLY = False

print("="*60)
print("DESKTOP DATABASE SERVER (192.168.1.21)")
print(f"   Default: {DEFAULT_DATABASE}")
print("="*60)

def get_connection(database: str = None):
    """Connect to Desktop's local PostgreSQL"""
    config = BASE_CONFIG.copy()
    config["database"] = database or DEFAULT_DATABASE
    return psycopg2.connect(**config)

def execute_query(query: str, database: str = None, params: tuple = None) -> dict:
    """Execute query on DESKTOP database"""
    try:
        conn = get_connection(database)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if READ_ONLY:
            query_upper = query.strip().upper()
            if any(keyword in query_upper for keyword in ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER', 'TRUNCATE']):
                return {"error": "Write operations disabled", "server": "DESKTOP"}
        
        cursor.execute(query, params)
        
        if cursor.description:
            rows = cursor.fetchmany(MAX_ROWS)
            columns = [desc[0] for desc in cursor.description]
            has_more = cursor.fetchone() is not None
            
            result = {
                "columns": columns,
                "rows": [dict(row) for row in rows],
                "row_count": len(rows),
                "has_more": has_more,
                "database": database or DEFAULT_DATABASE,
                "server": "DESKTOP"
            }
        else:
            conn.commit()
            result = {
                "affected_rows": cursor.rowcount,
                "message": "Query executed successfully",
                "database": database or DEFAULT_DATABASE,
                "server": "DESKTOP"
            }
        
        cursor.close()
        conn.close()
        return result
    
    except Exception as e:
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return {"error": str(e), "server": "DESKTOP"}


@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="desktop_list_databases",
            description="[DESKTOP] List all databases on Windows Desktop PostgreSQL",
            inputSchema={"type": "object", "properties": {}}
        ),
        Tool(
            name="desktop_create_database",
            description="[DESKTOP] Create a new database on Desktop",
            inputSchema={
                "type": "object",
                "properties": {
                    "database_name": {"type": "string", "description": "Name of the database to create"},
                    "owner": {"type": "string", "description": "Database owner (default: current user)"},
                    "encoding": {"type": "string", "description": "Character encoding (default: UTF8)"}
                },
                "required": ["database_name"]
            }
        ),
        Tool(
            name="desktop_drop_database",
            description="[DESKTOP] Drop/delete a database on Desktop (DANGEROUS - requires confirmation)",
            inputSchema={
                "type": "object",
                "properties": {
                    "database_name": {"type": "string", "description": "Name of the database to drop"},
                    "confirm": {"type": "boolean", "description": "Must be true to confirm deletion"}
                },
                "required": ["database_name", "confirm"]
            }
        ),
        Tool(
            name="desktop_create_table",
            description="[DESKTOP] Create a new table with columns, constraints, and foreign keys",
            inputSchema={
                "type": "object",
                "properties": {
                    "database": {"type": "string", "description": f"Database name (default: {DEFAULT_DATABASE})"},
                    "table_name": {"type": "string", "description": "Name of the table"},
                    "schema": {"type": "string", "description": "Schema name (default: public)", "default": "public"},
                    "columns": {
                        "type": "array",
                        "description": "Array of column definitions",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string", "description": "Column name"},
                                "type": {"type": "string", "description": "Data type (e.g., INTEGER, VARCHAR(255), TEXT, TIMESTAMP)"},
                                "nullable": {"type": "boolean", "description": "Can be NULL (default: true)", "default": True},
                                "primary_key": {"type": "boolean", "description": "Is primary key", "default": False},
                                "unique": {"type": "boolean", "description": "Must be unique", "default": False},
                                "default": {"type": "string", "description": "Default value"},
                                "check": {"type": "string", "description": "CHECK constraint (e.g., 'age > 0')"}
                            },
                            "required": ["name", "type"]
                        }
                    },
                    "foreign_keys": {
                        "type": "array",
                        "description": "Array of foreign key definitions",
                        "items": {
                            "type": "object",
                            "properties": {
                                "column": {"type": "string", "description": "Column in this table"},
                                "references_table": {"type": "string", "description": "Referenced table name"},
                                "references_column": {"type": "string", "description": "Referenced column name"},
                                "on_delete": {"type": "string", "description": "ON DELETE action (CASCADE, SET NULL, RESTRICT)", "default": "RESTRICT"},
                                "on_update": {"type": "string", "description": "ON UPDATE action (CASCADE, SET NULL, RESTRICT)", "default": "RESTRICT"}
                            },
                            "required": ["column", "references_table", "references_column"]
                        }
                    }
                },
                "required": ["table_name", "columns"]
            }
        ),
        Tool(
            name="desktop_drop_table",
            description="[DESKTOP] Drop/delete a table (DANGEROUS - requires confirmation)",
            inputSchema={
                "type": "object",
                "properties": {
                    "database": {"type": "string", "description": f"Database name (default: {DEFAULT_DATABASE})"},
                    "table_name": {"type": "string", "description": "Name of the table to drop"},
                    "schema": {"type": "string", "description": "Schema name (default: public)", "default": "public"},
                    "cascade": {"type": "boolean", "description": "Drop dependent objects too", "default": False},
                    "confirm": {"type": "boolean", "description": "Must be true to confirm deletion"}
                },
                "required": ["table_name", "confirm"]
            }
        ),
        Tool(
            name="desktop_add_column",
            description="[DESKTOP] Add a new column to an existing table",
            inputSchema={
                "type": "object",
                "properties": {
                    "database": {"type": "string", "description": f"Database name (default: {DEFAULT_DATABASE})"},
                    "table_name": {"type": "string", "description": "Table name"},
                    "schema": {"type": "string", "description": "Schema (default: public)", "default": "public"},
                    "column_name": {"type": "string", "description": "New column name"},
                    "data_type": {"type": "string", "description": "Data type"},
                    "nullable": {"type": "boolean", "description": "Can be NULL", "default": True},
                    "default": {"type": "string", "description": "Default value"}
                },
                "required": ["table_name", "column_name", "data_type"]
            }
        ),
        Tool(
            name="desktop_drop_column",
            description="[DESKTOP] Remove a column from a table",
            inputSchema={
                "type": "object",
                "properties": {
                    "database": {"type": "string", "description": f"Database name (default: {DEFAULT_DATABASE})"},
                    "table_name": {"type": "string", "description": "Table name"},
                    "schema": {"type": "string", "description": "Schema (default: public)", "default": "public"},
                    "column_name": {"type": "string", "description": "Column to drop"},
                    "confirm": {"type": "boolean", "description": "Must be true to confirm"}
                },
                "required": ["table_name", "column_name", "confirm"]
            }
        ),
        Tool(
            name="desktop_create_index",
            description="[DESKTOP] Create an index on table column(s)",
            inputSchema={
                "type": "object",
                "properties": {
                    "database": {"type": "string", "description": f"Database name (default: {DEFAULT_DATABASE})"},
                    "table_name": {"type": "string", "description": "Table name"},
                    "schema": {"type": "string", "description": "Schema (default: public)", "default": "public"},
                    "index_name": {"type": "string", "description": "Index name (auto-generated if not provided)"},
                    "columns": {"type": "array", "items": {"type": "string"}, "description": "Column names to index"},
                    "unique": {"type": "boolean", "description": "Create unique index", "default": False},
                    "method": {"type": "string", "description": "Index method (btree, hash, gin, gist)", "default": "btree"}
                },
                "required": ["table_name", "columns"]
            }
        ),
        Tool(
            name="desktop_drop_index",
            description="[DESKTOP] Drop an index",
            inputSchema={
                "type": "object",
                "properties": {
                    "database": {"type": "string", "description": f"Database name (default: {DEFAULT_DATABASE})"},
                    "index_name": {"type": "string", "description": "Index name to drop"},
                    "schema": {"type": "string", "description": "Schema (default: public)", "default": "public"},
                    "confirm": {"type": "boolean", "description": "Must be true to confirm"}
                },
                "required": ["index_name", "confirm"]
            }
        ),
        Tool(
            name="desktop_add_foreign_key",
            description="[DESKTOP] Add a foreign key constraint to existing table",
            inputSchema={
                "type": "object",
                "properties": {
                    "database": {"type": "string", "description": f"Database name (default: {DEFAULT_DATABASE})"},
                    "table_name": {"type": "string", "description": "Table name"},
                    "schema": {"type": "string", "description": "Schema (default: public)", "default": "public"},
                    "constraint_name": {"type": "string", "description": "Constraint name"},
                    "column": {"type": "string", "description": "Column in this table"},
                    "references_table": {"type": "string", "description": "Referenced table"},
                    "references_column": {"type": "string", "description": "Referenced column"},
                    "on_delete": {"type": "string", "description": "ON DELETE action", "default": "RESTRICT"},
                    "on_update": {"type": "string", "description": "ON UPDATE action", "default": "RESTRICT"}
                },
                "required": ["table_name", "constraint_name", "column", "references_table", "references_column"]
            }
        ),
        Tool(
            name="desktop_execute_query",
            description="[DESKTOP] Execute SQL query on Desktop database (afterburner by default)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "SQL query"},
                    "database": {"type": "string", "description": f"Database name (default: {DEFAULT_DATABASE})"}
                },
                "required": ["query"]
            }
        ),
        Tool(
            name="desktop_list_tables",
            description="[DESKTOP] List tables in Desktop database",
            inputSchema={
                "type": "object",
                "properties": {
                    "database": {"type": "string", "description": f"Database (default: {DEFAULT_DATABASE})"},
                    "schema": {"type": "string", "description": "Schema (default: public)", "default": "public"}
                }
            }
        ),
        Tool(
            name="desktop_describe_table",
            description="[DESKTOP] Get table structure on Desktop database",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_name": {"type": "string", "description": "Table name"},
                    "database": {"type": "string", "description": f"Database (default: {DEFAULT_DATABASE})"},
                    "schema": {"type": "string", "description": "Schema (default: public)", "default": "public"}
                },
                "required": ["table_name"]
            }
        ),
        Tool(
            name="desktop_table_statistics",
            description="[DESKTOP] Get table statistics on Desktop database",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_name": {"type": "string"},
                    "database": {"type": "string", "description": f"Database (default: {DEFAULT_DATABASE})"},
                    "schema": {"type": "string", "default": "public"}
                },
                "required": ["table_name"]
            }
        ),
        Tool(
            name="desktop_column_statistics",
            description="[DESKTOP] Get column statistics on Desktop database",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_name": {"type": "string"},
                    "column_name": {"type": "string"},
                    "database": {"type": "string", "description": f"Database (default: {DEFAULT_DATABASE})"},
                    "schema": {"type": "string", "default": "public"}
                },
                "required": ["table_name", "column_name"]
            }
        ),
        Tool(
            name="desktop_get_indexes",
            description="[DESKTOP] List indexes on Desktop database",
            inputSchema={
                "type": "object",
                "properties": {
                    "table_name": {"type": "string"},
                    "database": {"type": "string", "description": f"Database (default: {DEFAULT_DATABASE})"},
                    "schema": {"type": "string", "default": "public"}
                },
                "required": ["table_name"]
            }
        ),
        Tool(
            name="desktop_database_summary",
            description="[DESKTOP] Get database summary on Desktop",
            inputSchema={
                "type": "object",
                "properties": {
                    "database": {"type": "string", "description": f"Database (default: {DEFAULT_DATABASE})"}
                }
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    
    tool_name = name.replace("desktop_", "")
    
    if tool_name == "create_database":
        db_name = arguments["database_name"]
        owner = arguments.get("owner")
        encoding = arguments.get("encoding", "UTF8")
        
        try:
            conn = get_connection("postgres")
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            query = f'CREATE DATABASE "{db_name}"'
            if owner:
                query += f' OWNER "{owner}"'
            query += f" ENCODING '{encoding}'"
            
            cursor.execute(query)
            cursor.close()
            conn.close()
            
            return [TextContent(type="text", text=f"[DESKTOP] Database '{db_name}' created successfully\nOwner: {owner or 'default'}\nEncoding: {encoding}")]
        
        except Exception as e:
            return [TextContent(type="text", text=f"[DESKTOP] Error creating database: {str(e)}")]
    
    elif tool_name == "drop_database":
        db_name = arguments["database_name"]
        confirm = arguments.get("confirm", False)
        
        if not confirm:
            return [TextContent(type="text", text=f"[DESKTOP] Database deletion not confirmed. Set 'confirm' to true to proceed.")]
        
        try:
            conn = get_connection("postgres")
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            cursor.execute(f'DROP DATABASE "{db_name}"')
            cursor.close()
            conn.close()
            
            return [TextContent(type="text", text=f"[DESKTOP] Database '{db_name}' dropped successfully")]
        
        except Exception as e:
            return [TextContent(type="text", text=f"[DESKTOP] Error dropping database: {str(e)}")]
    
    elif tool_name == "create_table":
        table_name = arguments["table_name"]
        columns = arguments["columns"]
        foreign_keys = arguments.get("foreign_keys", [])
        database = arguments.get("database")
        schema = arguments.get("schema", "public")
        
        col_defs = []
        for col in columns:
            col_def = f'"{col["name"]}" {col["type"]}'
            
            if col.get('primary_key'):
                col_def += " PRIMARY KEY"
            if not col.get('nullable', True):
                col_def += " NOT NULL"
            if col.get('unique'):
                col_def += " UNIQUE"
            if col.get('default'):
                col_def += f" DEFAULT {col['default']}"
            if col.get('check'):
                col_def += f" CHECK ({col['check']})"
            
            col_defs.append(col_def)
        
        for fk in foreign_keys:
            fk_def = f'FOREIGN KEY ("{fk["column"]}") REFERENCES "{fk["references_table"]}"("{fk["references_column"]}")'
            if fk.get('on_delete'):
                fk_def += f" ON DELETE {fk['on_delete']}"
            if fk.get('on_update'):
                fk_def += f" ON UPDATE {fk['on_update']}"
            col_defs.append(fk_def)
        
        query = f'CREATE TABLE "{schema}"."{table_name}" ({", ".join(col_defs)})'
        result = execute_query(query, database)
        
        if "error" in result:
            return [TextContent(type="text", text=f"[DESKTOP] Error creating table: {result['error']}")]
        
        output = f"[DESKTOP] Table '{schema}.{table_name}' created successfully\n\n"
        output += f"Columns: {len(columns)}\n"
        output += f"Foreign Keys: {len(foreign_keys)}\n\n"
        output += f"SQL: {query}"
        
        return [TextContent(type="text", text=output)]
    
    elif tool_name == "drop_table":
        table_name = arguments["table_name"]
        confirm = arguments.get("confirm", False)
        database = arguments.get("database")
        schema = arguments.get("schema", "public")
        cascade = arguments.get("cascade", False)
        
        if not confirm:
            return [TextContent(type="text", text=f"[DESKTOP] Table deletion not confirmed. Set 'confirm' to true to proceed.")]
        
        query = f'DROP TABLE "{schema}"."{table_name}"'
        if cascade:
            query += " CASCADE"
        
        result = execute_query(query, database)
        
        if "error" in result:
            return [TextContent(type="text", text=f"[DESKTOP] Error dropping table: {result['error']}")]
        
        return [TextContent(type="text", text=f"[DESKTOP] Table '{schema}.{table_name}' dropped successfully")]
    
    elif tool_name == "add_column":
        table_name = arguments["table_name"]
        column_name = arguments["column_name"]
        data_type = arguments["data_type"]
        database = arguments.get("database")
        schema = arguments.get("schema", "public")
        nullable = arguments.get("nullable", True)
        default = arguments.get("default")
        
        query = f'ALTER TABLE "{schema}"."{table_name}" ADD COLUMN "{column_name}" {data_type}'
        
        if not nullable:
            query += " NOT NULL"
        if default:
            query += f" DEFAULT {default}"
        
        result = execute_query(query, database)
        
        if "error" in result:
            return [TextContent(type="text", text=f"[DESKTOP] Error adding column: {result['error']}")]
        
        return [TextContent(type="text", text=f"[DESKTOP] Column '{column_name}' added to '{schema}.{table_name}'")]
    
    elif tool_name == "drop_column":
        table_name = arguments["table_name"]
        column_name = arguments["column_name"]
        confirm = arguments.get("confirm", False)
        database = arguments.get("database")
        schema = arguments.get("schema", "public")
        
        if not confirm:
            return [TextContent(type="text", text=f"[DESKTOP] Column deletion not confirmed. Set 'confirm' to true to proceed.")]
        
        query = f'ALTER TABLE "{schema}"."{table_name}" DROP COLUMN "{column_name}"'
        result = execute_query(query, database)
        
        if "error" in result:
            return [TextContent(type="text", text=f"[DESKTOP] Error dropping column: {result['error']}")]
        
        return [TextContent(type="text", text=f"[DESKTOP] Column '{column_name}' dropped from '{schema}.{table_name}'")]
    
    elif tool_name == "create_index":
        table_name = arguments["table_name"]
        columns = arguments["columns"]
        database = arguments.get("database")
        schema = arguments.get("schema", "public")
        index_name = arguments.get("index_name", f"idx_{table_name}_{'_'.join(columns)}")
        unique = arguments.get("unique", False)
        method = arguments.get("method", "btree")
        
        unique_keyword = "UNIQUE " if unique else ""
        columns_quoted = ', '.join([f'"{col}"' for col in columns])
        query = f'CREATE {unique_keyword}INDEX "{index_name}" ON "{schema}"."{table_name}" USING {method} ({columns_quoted})'
        
        result = execute_query(query, database)
        
        if "error" in result:
            return [TextContent(type="text", text=f"[DESKTOP] Error creating index: {result['error']}")]
        
        return [TextContent(type="text", text=f"[DESKTOP] Index '{index_name}' created on {schema}.{table_name}({', '.join(columns)})")]
    
    elif tool_name == "drop_index":
        index_name = arguments["index_name"]
        confirm = arguments.get("confirm", False)
        database = arguments.get("database")
        schema = arguments.get("schema", "public")
        
        if not confirm:
            return [TextContent(type="text", text=f"[DESKTOP] Index deletion not confirmed. Set 'confirm' to true to proceed.")]
        
        query = f'DROP INDEX "{schema}"."{index_name}"'
        result = execute_query(query, database)
        
        if "error" in result:
            return [TextContent(type="text", text=f"[DESKTOP] Error dropping index: {result['error']}")]
        
        return [TextContent(type="text", text=f"[DESKTOP] Index '{index_name}' dropped successfully")]
    
    elif tool_name == "add_foreign_key":
        table_name = arguments["table_name"]
        constraint_name = arguments["constraint_name"]
        column = arguments["column"]
        references_table = arguments["references_table"]
        references_column = arguments["references_column"]
        database = arguments.get("database")
        schema = arguments.get("schema", "public")
        on_delete = arguments.get("on_delete", "RESTRICT")
        on_update = arguments.get("on_update", "RESTRICT")
        
        query = f'ALTER TABLE "{schema}"."{table_name}" ADD CONSTRAINT "{constraint_name}" '
        query += f'FOREIGN KEY ("{column}") REFERENCES "{references_table}"("{references_column}") '
        query += f"ON DELETE {on_delete} ON UPDATE {on_update}"
        
        result = execute_query(query, database)
        
        if "error" in result:
            return [TextContent(type="text", text=f"[DESKTOP] Error adding foreign key: {result['error']}")]
        
        return [TextContent(type="text", text=f"[DESKTOP] Foreign key '{constraint_name}' added to '{schema}.{table_name}'")]
    
    elif tool_name == "list_databases":
        query = """
            SELECT 
                datname as database_name,
                pg_size_pretty(pg_database_size(datname)) as size,
                (SELECT count(*) FROM pg_stat_activity WHERE datname = d.datname) as connections
            FROM pg_database d
            WHERE datistemplate = false
            ORDER BY pg_database_size(datname) DESC
        """
        result = execute_query(query, "postgres")
        
        if "error" in result:
            return [TextContent(type="text", text=f"[DESKTOP] Error: {result['error']}")]
        
        output = "[DESKTOP] Available Databases:\n\n"
        for row in result['rows']:
            default_marker = " <- DEFAULT" if row['database_name'] == DEFAULT_DATABASE else ""
            output += f"* {row['database_name']}{default_marker}\n"
            output += f"  Size: {row['size']}\n"
            output += f"  Connections: {row['connections']}\n\n"
        
        return [TextContent(type="text", text=output)]
    
    elif tool_name == "execute_query":
        query = arguments["query"]
        database = arguments.get("database")
        result = execute_query(query, database)
        
        if "error" in result:
            return [TextContent(type="text", text=f"[DESKTOP] Error: {result['error']}")]
        
        if "rows" in result:
            output = f"[DESKTOP] Database: {result['database']}\n"
            output += f"Query returned {result['row_count']} rows"
            if result['has_more']:
                output += f" (limited to {MAX_ROWS})"
            output += "\n\n"
            output += json.dumps(result['rows'], indent=2, default=str)
        else:
            output = f"[DESKTOP] Database: {result['database']}\n"
            output += f"{result['message']}\nAffected rows: {result['affected_rows']}"
        
        return [TextContent(type="text", text=output)]
    
    elif tool_name == "list_tables":
        database = arguments.get("database")
        schema = arguments.get("schema", "public")
        
        query = """
            SELECT table_name, table_type
            FROM information_schema.tables
            WHERE table_schema = %s
            ORDER BY table_name
        """
        result = execute_query(query, database, (schema,))
        
        if "error" in result:
            return [TextContent(type="text", text=f"[DESKTOP] Error: {result['error']}")]
        
        output = f"[DESKTOP] Database: {result['database']}\n"
        output += f"Tables in schema '{schema}':\n\n"
        for row in result['rows']:
            output += f"* {row['table_name']} ({row['table_type']})\n"
        
        return [TextContent(type="text", text=output)]
    
    elif tool_name == "describe_table":
        table_name = arguments["table_name"]
        database = arguments.get("database")
        schema = arguments.get("schema", "public")
        
        query = """
            SELECT column_name, data_type, character_maximum_length, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = %s AND table_schema = %s
            ORDER BY ordinal_position
        """
        result = execute_query(query, database, (table_name, schema))
        
        if "error" in result:
            return [TextContent(type="text", text=f"[DESKTOP] Error: {result['error']}")]
        
        output = f"[DESKTOP] Database: {result['database']}\n"
        output += f"Structure of '{schema}.{table_name}':\n\n"
        for row in result['rows']:
            nullable = "NULL" if row['is_nullable'] == 'YES' else "NOT NULL"
            type_info = row['data_type']
            if row['character_maximum_length']:
                type_info += f"({row['character_maximum_length']})"
            output += f"* {row['column_name']}: {type_info} {nullable}\n"
            if row['column_default']:
                output += f"  Default: {row['column_default']}\n"
        
        return [TextContent(type="text", text=output)]
    
    elif tool_name == "table_statistics":
        table_name = arguments["table_name"]
        database = arguments.get("database")
        schema = arguments.get("schema", "public")
        
        query = f"""
            SELECT 
                (SELECT COUNT(*) FROM "{schema}"."{table_name}") as row_count,
                pg_size_pretty(pg_total_relation_size('"{schema}"."{table_name}"')) as total_size
        """
        result = execute_query(query, database)
        
        if "error" in result:
            return [TextContent(type="text", text=f"[DESKTOP] Error: {result['error']}")]
        
        if result['rows']:
            stats = result['rows'][0]
            output = f"[DESKTOP] Database: {result['database']}\n"
            output += f"Statistics for '{schema}.{table_name}':\n\n"
            output += f"* Row count: {stats['row_count']:,}\n"
            output += f"* Total size: {stats['total_size']}\n"
        else:
            output = f"[DESKTOP] Could not retrieve statistics"
        
        return [TextContent(type="text", text=output)]
    
    elif tool_name == "column_statistics":
        table_name = arguments["table_name"]
        column_name = arguments["column_name"]
        database = arguments.get("database")
        schema = arguments.get("schema", "public")
        
        query = f"""
            SELECT 
                COUNT(*) as total_rows,
                COUNT("{column_name}") as non_null_count,
                COUNT(DISTINCT "{column_name}") as distinct_count
            FROM "{schema}"."{table_name}"
        """
        result = execute_query(query, database)
        
        if "error" in result:
            return [TextContent(type="text", text=f"[DESKTOP] Error: {result['error']}")]
        
        if result['rows']:
            stats = result['rows'][0]
            output = f"[DESKTOP] Database: {result['database']}\n"
            output += f"Statistics for column '{column_name}':\n\n"
            output += f"* Total rows: {stats['total_rows']:,}\n"
            output += f"* Non-null values: {stats['non_null_count']:,}\n"
            output += f"* Distinct values: {stats['distinct_count']:,}\n"
        else:
            output = f"[DESKTOP] Could not retrieve statistics"
        
        return [TextContent(type="text", text=output)]
    
    elif tool_name == "get_indexes":
        table_name = arguments["table_name"]
        database = arguments.get("database")
        schema = arguments.get("schema", "public")
        
        query = """
            SELECT
                indexname,
                indexdef,
                pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size
            FROM pg_indexes
            WHERE schemaname = %s AND tablename = %s
            ORDER BY indexname
        """
        result = execute_query(query, database, (schema, table_name))
        
        if "error" in result:
            return [TextContent(type="text", text=f"[DESKTOP] Error: {result['error']}")]
        
        output = f"[DESKTOP] Database: {result['database']}\n"
        output += f"Indexes for '{schema}.{table_name}':\n\n"
        if result['rows']:
            for row in result['rows']:
                output += f"* {row['indexname']} ({row['index_size']})\n"
                output += f"  {row['indexdef']}\n\n"
        else:
            output += "No indexes found"
        
        return [TextContent(type="text", text=output)]
    
    elif tool_name == "database_summary":
        database = arguments.get("database")
        
        query = """
            SELECT 
                (SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public') as table_count,
                pg_size_pretty(pg_database_size(current_database())) as total_size,
                current_database() as database_name
        """
        result = execute_query(query, database)
        
        if "error" in result:
            return [TextContent(type="text", text=f"[DESKTOP] Error: {result['error']}")]
        
        if result['rows']:
            summary = result['rows'][0]
            output = f"[DESKTOP] Database: '{summary['database_name']}'\n\n"
            output += f"* Total size: {summary['total_size']}\n"
            output += f"* Tables: {summary['table_count']}\n"
        else:
            output = f"[DESKTOP] Could not retrieve summary"
        
        return [TextContent(type="text", text=output)]
    
    # Fallback for unimplemented tools
    return [TextContent(type="text", text=f"[DESKTOP] Tool '{name}' not implemented")]


async def main():
    print("PostgreSQL MCP Server (DESKTOP) started")
    print(f"Host: {BASE_CONFIG['host']}:{BASE_CONFIG['port']}")
    print(f"Default database: {DEFAULT_DATABASE}")
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())