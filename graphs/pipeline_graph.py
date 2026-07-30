from langgraph.graph import StateGraph, START, END

from graphs.state import PipelineState
from graphs.nodes import (
    clone_node,
    index_node,
    architecture_node,
    summary_node,
    fetch_pr_node,
    build_diff_node,
    retrieve_context_node,
    review_node,
    security_node,
    performance_node,
    testing_node,
    architecture_review_node,
    documentation_node,
    judge_node,
    kitsune_fix_node
)


def build_pipeline_graph():
    graph = StateGraph(PipelineState)

    graph.add_node("clone", clone_node)
    graph.add_node("index", index_node)
    graph.add_node("architecture", architecture_node)
    graph.add_node("summary", summary_node)
    graph.add_node("fetch_pr", fetch_pr_node)
    graph.add_node("build_diff", build_diff_node)
    graph.add_node("retrieve_context", retrieve_context_node)
    graph.add_node("review", review_node)
    graph.add_node("security", security_node)
    graph.add_node("performance", performance_node)
    graph.add_node("testing", testing_node)
    graph.add_node("architecture_review", architecture_review_node)
    graph.add_node("documentation", documentation_node)
    graph.add_node("judge", judge_node)
    graph.add_node("kitsune_fix", kitsune_fix_node)

    graph.add_edge(START, "clone")
    graph.add_edge("clone", "index")
    graph.add_edge("index", "architecture")
    graph.add_edge("architecture", "summary")
    graph.add_edge("summary", "fetch_pr")
    graph.add_edge("fetch_pr", "build_diff")
    graph.add_edge("build_diff", "retrieve_context")
    graph.add_edge("retrieve_context", "review")
    graph.add_edge("retrieve_context", "security")
    graph.add_edge("retrieve_context", "performance")
    graph.add_edge("retrieve_context", "testing")
    graph.add_edge("retrieve_context", "architecture_review")
    graph.add_edge("retrieve_context", "documentation")
    
    graph.add_edge("review", "judge")
    graph.add_edge("security", "judge")
    graph.add_edge("performance", "judge")
    graph.add_edge("testing", "judge")
    graph.add_edge("architecture_review", "judge")
    graph.add_edge("documentation", "judge")
    
    graph.add_edge("judge", "kitsune_fix")
    graph.add_edge("kitsune_fix", END)

    return graph.compile()
