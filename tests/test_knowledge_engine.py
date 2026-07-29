import sys
import io
import os
import json

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv()

ARCHFOX_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ARCHFOX_ROOT not in sys.path:
    sys.path.insert(0, ARCHFOX_ROOT)

from kitsune.engine.knowledge_engine import RepositoryKnowledgeEngine


def main():
    print("Testing the Repository Knowledge Engine (RKE)...")
    
    try:
        engine = RepositoryKnowledgeEngine()
        print("✅ RKE initialized successfully.")
    except Exception as e:
        print(f"❌ Failed to initialize RKE: {e}")
        return

    # 1. Test Semantic Search
    print("\n--- 1. Testing Semantic Search ---")
    query = "How is the fix payload generated?"
    context = engine.search_semantic(query, top_k=2)
    print(f"Returned Context Length: {len(context)} characters")
    
    # 2. Test fetching exact Source Code
    print("\n--- 2. Testing Source Code Retrieval ---")
    code = engine.get_source_code("generate_fix_payload")
    if code:
        print(f"Found source code for 'generate_fix_payload':\n{code[:150]}...")
    else:
        print("Could not find 'generate_fix_payload' in ChromaDB (maybe it's not indexed).")

    # 3. Test Graph Topologies
    print("\n--- 3. Testing Graph Topologies ---")
    call_graph = engine.get_call_graph("generate_fix_payload")
    print(json.dumps(call_graph, indent=2))
    print("\n✅ Verification complete!")

if __name__ == "__main__":
    main()
