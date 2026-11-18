import json
import os

from langchain_core.tools import tool

from configs.logger import get_logger
from tools.kitsune_engine import active_engine

logger = get_logger(__name__)

# The graph tools query Kitsune's call graph for the repository under review
# (set by index_node). Kitsune resolves real call targets (types, imports,
# dependency injection), and runs on NetworkX when no Neo4j server is configured,
# so these tools work in the GitHub Action without a database.


@tool
def get_upstream_callers(function_name: str) -> str:
    """
    Finds all functions that call a specific function (up to 2 hops).
    Use this when a function is modified to see what other parts of the codebase might break.
    """
    logger.info(f"Agent called tool: get_upstream_callers('{function_name}')")
    callers = active_engine().get_upstream_callers(function_name, depth=2)
    if not callers:
        return "No upstream callers found."
    return json.dumps(callers)


@tool
def get_dependencies(function_name: str) -> str:
    """
    Finds everything a specific function calls (up to 2 hops).
    Use this to understand what a function relies on.
    """
    logger.info(f"Agent called tool: get_dependencies('{function_name}')")
    deps = active_engine().get_downstream_dependencies(function_name, depth=2)
    if not deps:
        return "No dependencies found."
    return json.dumps(deps)


@tool
def get_impact_analysis(function_name: str) -> str:
    """
    Blast radius of changing a function: every caller and dependency up to 3 hops.
    Use this before flagging a change as risky, to see how much code it can affect.
    """
    logger.info(f"Agent called tool: get_impact_analysis('{function_name}')")
    impact = active_engine().get_impact_analysis(function_name, max_depth=3)
    if not impact or not impact.get("total_impact"):
        return "No impact found (the function has no known callers or dependencies)."
    return json.dumps(impact, default=str)


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
            content = f.read()
            if not content.strip():
                return f"File {file_path} is empty."
            return content
    except Exception as e:
        return f"Error reading file: {str(e)}"


# We bundle these together so we can easily pass them to the LangGraph agents
AGENT_TOOLS = [get_upstream_callers, get_dependencies, get_impact_analysis, read_file_content]
