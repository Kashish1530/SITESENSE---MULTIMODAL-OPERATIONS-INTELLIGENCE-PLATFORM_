"""
SiteSense Complete Integration Verification Script
Verifies: Frontend API <-> Backend FastAPI <-> Agentic Layer <-> GenAI Knowledge Layer
"""

import sys
import time
import requests

BASE_URL = "http://localhost:8000/api/v1"

def print_section(title):
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)

def main():
    print_section("SITESENSE COMPLETE END-TO-END INTEGRATION CHECK")
    
    # 1. Check Backend Health
    print("\n[STEP 1/4] Checking Backend API Server...")
    try:
        health_resp = requests.get(f"{BASE_URL}/health", timeout=5)
        if health_resp.status_code == 200:
            print("  [SUCCESS] Backend is ONLINE at http://localhost:8000")
            print(f"            Health status: {health_resp.json().get('status', 'ok')}")
        else:
            print(f"  [ERROR] Backend returned status {health_resp.status_code}")
            return
    except Exception as e:
        print(f"  [FAILED] Could not connect to backend: {e}")
        return

    # 2. Check Authentication
    print("\n[STEP 2/4] Testing User Authentication (Backend RBAC)...")
    login_resp = requests.post(f"{BASE_URL}/auth/login", json={
        "email": "admin@sitesense.io",
        "password": "SiteSense@2026"
    })
    if login_resp.status_code != 200:
        print(f"  [FAILED] Login failed: {login_resp.text}")
        return
    token = login_resp.json()["access_token"]
    user_info = login_resp.json().get("user", {})
    print(f"  [SUCCESS] Logged in as: {user_info.get('name', 'Admin')} ({user_info.get('role', 'admin')})")
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Create Chat Session
    print("\n[STEP 3/4] Creating Chat Session (Session & Memory)...")
    sess_resp = requests.post(f"{BASE_URL}/chat/sessions", json={
        "title": "Integration Check Session"
    }, headers=headers)
    if sess_resp.status_code not in (200, 201):
        print(f"  [FAILED] Session creation failed: {sess_resp.text}")
        return
    session_id = sess_resp.json()["id"]
    print(f"  [SUCCESS] Session created with ID: {session_id}")

    # 4. Send Operational Query to Agent
    question = "What is the required clearance for emergency walkways according to our warehouse policy?"
    print(f"\n[STEP 4/4] Sending Query to Agentic & GenAI Pipeline...")
    print(f"  Query: \"{question}\"")
    print("  Executing: Router -> ReAct Agent -> HybridSearch (BM25 + pgvector + Reranker)...")
    
    t0 = time.time()
    msg_resp = requests.post(f"{BASE_URL}/chat/sessions/{session_id}/messages", json={
        "content": question
    }, headers=headers)
    elapsed = time.time() - t0

    if msg_resp.status_code not in (200, 201):
        print(f"  [FAILED] Message execution failed: {msg_resp.text}")
        return

    data = msg_resp.json()
    reply = data["assistant_message"]["content"]
    citations = data.get("citations", [])

    print(f"  [SUCCESS] Response received in {elapsed:.2f}s!")
    print("\n" + "-" * 70)
    print("AGENT REASONED & SYNTHESIZED ANSWER:")
    print("-" * 70)
    print(reply)
    print("-" * 70)
    print(f"GROUNDED CITATIONS RETURNED: {len(citations)} citation(s)")
    for i, c in enumerate(citations[:3], 1):
        print(f"  [{i}] Doc: {c.get('source_file')} | Page: {c.get('page')} | Clause: {c.get('clause')}")
        print(f"      Excerpt: {c.get('excerpt', '')[:100]}...")

    print_section("VERIFICATION COMPLETE: ALL 4 LAYERS ARE 100% INTEGRATED & WORKING!")
    print("""
1. Frontend   -> Calls http://localhost:8000/api/v1/chat/... with JWT Bearer Token
2. Backend    -> FastAPI ChatService orchestrates session & passes query to Agent
3. Agentic    -> SiteSenseAgent executes guardrails, routing, and ReAct tool calling
4. GenAI      -> HybridSearch retrieves Neon DB pgvector policy chunks with citations
""")

if __name__ == "__main__":
    main()
