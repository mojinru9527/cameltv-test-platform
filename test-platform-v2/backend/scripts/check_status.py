"""Quick check: wiki job status, wiki pages, KB sources, RAG search."""
import httpx, json, sys

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwiZXhwIjoxNzgzOTk1MzUzfQ.gW1PlU3TJ0G3Kjcd4hToyRpdV5a1EIxsO7Wgr8ei1C8"
HEADERS = {"Authorization": f"Bearer {TOKEN}", "X-Project-Id": "1"}
BASE = "http://127.0.0.1:8000/api/v1"

def get(path):
    r = httpx.get(f"{BASE}{path}", headers=HEADERS, timeout=15)
    return r.json()

def post(path, body):
    r = httpx.post(f"{BASE}{path}", headers=HEADERS, json=body, timeout=15)
    return r.json()

# 1. Wiki Job
d = get("/wiki/ingest-jobs/1")
job = d.get("data", {})
print(f"=== Wiki Job #1: status={job.get('status')}, stage={job.get('stage')}")
if job.get("result_json"):
    result = json.loads(job["result_json"])
    print(f"  pages={result.get('pages')}, review_items={result.get('review_items')}")
if job.get("error_message"):
    print(f"  ERROR: {job['error_message'][:200]}")

# 2. KB Overview
d = get("/knowledge/overview")
ov = d.get("data", {})
print(f"\n=== KB: {ov.get('source_count')} sources, {ov.get('chunk_count')} chunks")

# 3. Wiki Pages
d = get("/wiki/pages?page=1&page_size=20")
items = d.get("data", {}).get("items", []) or []
print(f"\n=== Wiki Pages: {len(items)}")
for p in items:
    print(f"  [{p.get('page_type')}] {p.get('title')}")

# 4. RAG Search
d = post("/knowledge/search", {"query": "test requirements", "mode": "keyword", "top_k": 5})
hits = d.get("data", []) or []
print(f"\n=== RAG Search: {len(hits)} hits")
for h in hits:
    print(f"  [{h.get('chunk_type')}] {h.get('title')} (score={h.get('score')})")
