from langchain_core.tools import tool
import os
from configs.logger import get_logger
from kitsune.graph.neo4j_store import Neo4jStore

logger = get_logger(__name__)

# Initialize a global connection to Neo4j for the tools to use
neo4j = Neo4jStore()

@tool
def get_upstream_callers(function_name: str) -> list[str]:
    """
    Finds all functions that call a specific function. 
    Use this when a function is modified to see what other parts of the codebase might break.
    """
    logger.info(f"Agent called tool: get_upstream_callers('{function_name}')")
    callers = neo4j.get_upstream_callers(function_name)
    return callers

@tool
def get_dependencies(function_name: str) -> list[str]:
    """
    Finds everything a specific function calls.
    Use this to understand what a function relies on.
    """
    logger.info(f"Agent called tool: get_dependencies('{function_name}')")
    deps = neo4j.get_dependencies(function_name)
    return deps

@tool
def read_file_content(file_path: str) -> str:
    """
    Reads the full content of a file from the repository.
    Use this when you need to see the exact implementation of a file that was not provided in your context.
    """
    logger.info(f"Agent called tool: read_file_content('{file_path}')")
    # Because the agent runs from the root of the clone, we can just read it
    if not os.path.exists(file_path):
        return f"Error: File {file_path} does not exist."
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"

# We bundle these together so we can easily pass them to the LangGraph agents
AGENT_TOOLS = [get_upstream_callers, get_dependencies, read_file_content]
