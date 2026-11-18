"""Smoke test: ArchFox's Kitsune integration on a tiny throwaway repository.

    python tests/test_knowledge_engine.py

Indexes a 2-file Python repo through tools.kitsune_engine (the same path the review
pipeline uses), then checks search, source lookup, the call graph and the agent tools.
Needs the embedding model (downloaded once); makes no LLM calls.
"""
import io
import json
import os
import sys
import tempfile
import textwrap

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ARCHFOX_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ARCHFOX_ROOT not in sys.path:
    sys.path.insert(0, ARCHFOX_ROOT)

FILES = {
    "payments.py": '''
        class StripeGateway:
            def charge(self, amount: int) -> bool:
                """Charge a card through Stripe."""
                return amount > 0
    ''',
    "checkout.py": '''
        from payments import StripeGateway

        def generate_fix_payload(order_total: int) -> bool:
            """Checkout entry point used by the test."""
            gateway = StripeGateway()
            return gateway.charge(order_total)
    ''',
}


def main() -> int:
    data = tempfile.mkdtemp(prefix="archfox_kitsune_")
    os.environ["ARCHFOX_KITSUNE_DATA"] = data
    repo = tempfile.mkdtemp(prefix="archfox_repo_")
    for name, code in FILES.items():
        with open(os.path.join(repo, name), "w", encoding="utf-8") as f:
            f.write(textwrap.dedent(code))

    from tools.kitsune_engine import namespace_for, set_active
    from tools.agent_tools import get_dependencies, get_impact_analysis, get_upstream_callers

    engine = set_active(namespace_for("test", "tiny-repo"))
    metrics = engine.index_repository(repo)
    print(metrics.summary())

    failures = []

    context = engine.search_semantic("How does checkout charge the card?")
    print(f"\nSearch context: {len(context)} characters")
    if "charge" not in context:
        failures.append("search did not return the charge code")

    code = engine.get_source_code("generate_fix_payload")
    print(f"Source found: {bool(code)}")
    if not code:
        failures.append("get_source_code found nothing")

    graph = engine.get_call_graph("generate_fix_payload")
    print("Call graph:", json.dumps(graph, default=str)[:300])

    callers = get_upstream_callers.invoke({"function_name": "charge"})
    deps = get_dependencies.invoke({"function_name": "generate_fix_payload"})
    impact = get_impact_analysis.invoke({"function_name": "charge"})
    print(f"Tool upstream callers of charge: {callers}")
    print(f"Tool dependencies of generate_fix_payload: {deps}")
    print(f"Tool impact of charge: {impact[:200]}")
    if "generate_fix_payload" not in callers:
        failures.append("charge() caller not resolved through the StripeGateway instance")
    if "charge" not in deps:
        failures.append("generate_fix_payload() dependency on charge() missing")

    print()
    if failures:
        for f in failures:
            print(f"❌ {f}")
        return 1
    print("✅ Kitsune integration works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
