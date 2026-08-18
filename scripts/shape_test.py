"""
Day 2 shape test: prove that a retrieval-augmented prompt reaches Qwen2.5-3B
and produces a coherent, structured response.

Not a benchmark. Runs once, prints result, exits.

Preconditions:
  - llama-server running at http://127.0.0.1:8080 with Qwen2.5-3B-Instruct Q4_K_M
  - document_chunks table populated (run scripts/ingest.py first)
  - sentence-transformers cached from ingestion
"""

import os
import sys
import json
import time
import sqlite3
import struct

os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from sentence_transformers import SentenceTransformer
import httpx

DB_PATH = "farmtwin.db"
LLAMA_URL = "http://127.0.0.1:8080/completion"
QUERY = "maize fungal disease risk vegetative stage humidity rainfall Kaduna"
TOP_K = 6

FARM_FACTS = {
    "farm_name": "Adamu's Farm",
    "region": "Kaduna, Nigeria",
    "area_hectares": 2.5,
    "field_name": "Main Field",
    "soil_type": "sandy loam",
    "crop": "maize",
    "variety": "SAMMAZ 15",
    "planting_date": "2026-06-12",
    "current_stage": "vegetative",
    "days_since_planting": 48,
    "recent_observations": [
        {"date": "2026-07-28", "type": "rainfall", "value": "65 mm over 48 hours"},
        {"date": "2026-07-29", "type": "humidity", "value": "85% sustained"},
    ],
}

QUESTION = (
    "Heavy rainfall and high humidity in the last 48 hours. "
    "What should this farmer do this week?"
)


def load_vec_extension(conn):
    conn.enable_load_extension(True)
    try:
        import sqlite_vec
        sqlite_vec.load(conn)
    finally:
        conn.enable_load_extension(False)


def retrieve_chunks(query_vec):
    conn = sqlite3.connect(DB_PATH)
    load_vec_extension(conn)
    vec_bytes = struct.pack(f"{len(query_vec)}f", *query_vec)
    rows = conn.execute(
        """
        SELECT dc.id, dc.source_org, dc.chunk_title, dc.content, v.distance
        FROM document_chunks_vec v
        JOIN document_chunks dc ON dc.id = v.chunk_id
        WHERE v.embedding MATCH ? AND k = ?
        ORDER BY v.distance
        """,
        (vec_bytes, TOP_K),
    ).fetchall()
    conn.close()
    return rows


def render_farm_yaml(d):
    lines = []
    for k, v in d.items():
        if k == "recent_observations":
            lines.append("recent_observations:")
            for obs in v:
                lines.append(f"  - date: {obs['date']}")
                lines.append(f"    type: {obs['type']}")
                lines.append(f"    value: {obs['value']}")
        else:
            lines.append(f"{k}: {v}")
    return "\n".join(lines)


def build_prompt(chunks):
    system = (
        "You are FarmTwin, an offline agricultural advisor.\n"
        "Answer using only the provided farm facts and knowledge chunks.\n"
        "Cite the knowledge chunks you rely on using their ID like [K1] or [K3].\n"
        "Distinguish clearly between farm facts, retrieved agricultural knowledge, "
        "predictions, and recommendations.\n"
        "\n"
        "Respond with a short narrative (3-6 sentences) that connects the farm's "
        "current state to relevant retrieved knowledge, followed by a fenced JSON "
        "block using this exact schema:\n"
        "```json\n"
        "{\n"
        '  "recommendations": [\n'
        '    {"what": "...", "why": "...", "when_urgency": "...", '
        '"risk_if_ignored": "...", "priority": "high|medium|low"}\n'
        "  ]\n"
        "}\n"
        "```"
    )

    knowledge_block = ""
    for i, (cid, org, title, content, dist) in enumerate(chunks, 1):
        knowledge_block += f"\n[K{i}] ({org}) {title}\n{content.strip()}\n"

    prompt = (
        f"<system>\n{system}\n</system>\n\n"
        f"<farm_facts>\n{render_farm_yaml(FARM_FACTS)}\n</farm_facts>\n\n"
        f"<knowledge>{knowledge_block}\n</knowledge>\n\n"
        f"<question>\n{QUESTION}\n</question>\n\n"
        "Respond now in the specified format."
    )
    return prompt


def main():
    print("Loading embedder (one-time PyTorch load)...")
    model = SentenceTransformer("all-MiniLM-L6-v2")
    qvec = model.encode(QUERY).tolist()
    print(f"Query embedded, dim={len(qvec)}")

    print(f"Retrieving top-{TOP_K} chunks...")
    chunks = retrieve_chunks(qvec)
    print(f"Retrieved {len(chunks)} chunks:")
    for i, (cid, org, title, content, dist) in enumerate(chunks, 1):
        print(f"  [K{i}] dist={dist:.4f}  {org} - {title}")

    prompt = build_prompt(chunks)
    char_count = len(prompt)
    approx_tokens = int(len(prompt.split()) * 1.3)
    print(f"\nPrompt: {char_count} chars, ~{approx_tokens} tokens")

    print("\nSending to llama-server...")
    t0 = time.time()
    resp = httpx.post(
        LLAMA_URL,
        json={
            "prompt": prompt,
            "n_predict": 600,
            "temperature": 0.3,
            "stop": ["</response>"],
        },
        timeout=300.0,
    )
    elapsed = time.time() - t0
    data = resp.json()
    content = data.get("content", "")

    print(f"\n=== Response received in {elapsed:.1f}s ===\n")
    print(content)
    print("\n=== End response ===\n")

    timings = data.get("timings", {})
    if timings:
        print(f"Prompt eval: {timings.get('prompt_ms', 0):.0f}ms "
              f"({timings.get('prompt_per_second', 0):.1f} tok/s)")
        print(f"Generation:  {timings.get('predicted_ms', 0):.0f}ms "
              f"({timings.get('predicted_per_second', 0):.1f} tok/s)")

    # Try to extract JSON block
    json_ok = False
    json_start = content.find("```json")
    if json_start != -1:
        rest = content[json_start + 7:]
        json_end = rest.find("```")
        if json_end != -1:
            try:
                parsed = json.loads(rest[:json_end].strip())
                json_ok = True
                print(f"\nJSON parsed OK. {len(parsed.get('recommendations', []))} recommendations.")
                print(json.dumps(parsed, indent=2))
            except json.JSONDecodeError as e:
                print(f"\nJSON found but failed to parse: {e}")

    if not json_ok:
        print("\nNo parseable JSON block in response.")

    print("\n=== SUMMARY ===")
    print(f"Prompt size:      {char_count} chars / ~{approx_tokens} tokens")
    print(f"Total time:       {elapsed:.1f}s")
    print(f"Generation speed: {timings.get('predicted_per_second', 0):.1f} tok/s")
    print(f"JSON parseable:   {'YES' if json_ok else 'NO'}")


if __name__ == "__main__":
    main()
