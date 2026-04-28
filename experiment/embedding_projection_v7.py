"""
Method 3 for v7: embedding-direction projection on risk-averse↔risk-tolerant axis.

Mirrors the v6 projection script (Bolukbasi-style direction-finding via
paired exemplars, projection of agent reasoning text), but with a new
direction defined for the risk-aversion preference dimension.

Backend priority: OpenAI text-embedding-3-small if OPENAI_API_KEY is set;
sentence-transformers all-MiniLM-L6-v2 (local, free) otherwise.

Usage:
  python embedding_projection_v7.py
"""

import json
import os
import statistics
from collections import defaultdict
from pathlib import Path

import numpy as np

RESULTS_DIR = Path(__file__).parent / "results"
PILOT_PATH = RESULTS_DIR / "v7_pilot_n5.json"
OUT_PATH = RESULTS_DIR / "v7_embedding_projection.json"


RISK_AVERSE_EXEMPLARS = [
    "Variance is a real cost; even if EV looks attractive, the chance of zero outcome means I weight the certain option more heavily.",
    "Multi-year commitments to partners are load-bearing; drawing them down for a higher-EV but uncertain bet is not a trade I'd make.",
    "Going to zero on a meaningful share of the budget creates partner-and-reputational damage that doesn't appear in the EV calculation.",
    "I'd allocate the bulk to the safe option and only commit a small exploratory share to the risky position.",
    "Predictability matters more than expected value here; the institutional context demands stability over upside.",
    "A 77.5% probability of zero is not something I'd accept for a meaningful fraction of unrestricted capital, regardless of EV.",
    "Real partner commitments and reputational considerations override the EV math when variance is this high.",
]

RISK_TOLERANT_EXEMPLARS = [
    "Capital preserved in the safe option contributes nothing to the cohort thesis; the entire point is to deploy into upside-bearing positions.",
    "Sure-but-mediocre outcomes are the actual underperformers; corner allocation to the high-EV risky position is the only correct answer.",
    "The EV multiplier of 1.46x dominates the safe option; any X<1 imports a variance-aversion the framework excludes.",
    "Power-law funds depend on full deployment into survival-conditional fund-returners; treasury allocation is slot-consumption with no upside.",
    "The framework explicitly does not weight variance separately, so the EV-positive position deserves full allocation.",
    "Holding back capital to avoid downside scenarios is exactly the slot-consumption-without-upside the strategy flags as the real underperformer.",
    "When EV per dollar in the risky leg exceeds the safe by a clear margin, the rational allocation is the corner.",
]


def _embed_openai(texts):
    import openai
    client = openai.OpenAI()
    resp = client.embeddings.create(model="text-embedding-3-small", input=texts)
    return np.array([d.embedding for d in resp.data], dtype=np.float64)


def _embed_local(texts):
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("all-MiniLM-L6-v2")
    embs = model.encode(texts, normalize_embeddings=False, show_progress_bar=False)
    return np.array(embs, dtype=np.float64)


def get_embedder():
    if os.environ.get("OPENAI_API_KEY"):
        return "openai (text-embedding-3-small)", _embed_openai
    return "local (sentence-transformers/all-MiniLM-L6-v2)", _embed_local


def compute_direction(embed_fn):
    averse = embed_fn(RISK_AVERSE_EXEMPLARS)
    tolerant = embed_fn(RISK_TOLERANT_EXEMPLARS)
    direction = tolerant.mean(axis=0) - averse.mean(axis=0)
    direction /= np.linalg.norm(direction)
    return direction, averse, tolerant


def project(embeddings, direction):
    return embeddings @ direction


def reasoning_text(r):
    return ((r.get("reasoning") or "") + " " + (r.get("thinking") or "")).strip()


def pearson(xs, ys):
    if len(xs) < 2:
        return None
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    return num / (dx * dy) if dx > 0 and dy > 0 else None


def main():
    backend_name, embed_fn = get_embedder()
    print(f"Embedder: {backend_name}\n")

    with open(PILOT_PATH, encoding="utf-8") as f:
        d = json.load(f)
    results = d["results"]
    print(f"Loaded {len(results)} agents from {PILOT_PATH.name}")

    print("\nComputing risk-averse ↔ risk-tolerant direction from paired exemplars...")
    direction, averse_e, tolerant_e = compute_direction(embed_fn)
    averse_proj = project(averse_e, direction)
    tolerant_proj = project(tolerant_e, direction)
    print(f"  exemplar projections: averse mean={averse_proj.mean():+.3f}, tolerant mean={tolerant_proj.mean():+.3f}")
    print(f"  separation (T - A): {tolerant_proj.mean() - averse_proj.mean():+.3f}\n")

    texts = [reasoning_text(r) for r in results]
    nonempty = [(i, t) for i, t in enumerate(texts) if t]
    print(f"Embedding {len(nonempty)} non-empty reasoning texts...")
    text_embs = embed_fn([t for _, t in nonempty])
    text_proj = project(text_embs, direction)
    proj_by_idx = {idx: float(text_proj[k]) for k, (idx, _) in enumerate(nonempty)}

    rows = []
    for i, r in enumerate(results):
        rows.append({
            "goal": r["goal"],
            "condition": r["condition"],
            "seed": r["seed"],
            "x": r.get("x"),
            "projection": proj_by_idx.get(i),
            "reasoning": reasoning_text(r),
        })

    print("=== Per cell × arm: projection mean (higher = more risk-tolerant) ===")
    print(f"{'goal':22s} {'arm':8s} {'n':>2s}  {'X mean':>7s} {'proj mean':>10s} {'proj sd':>8s}")
    for goal in sorted(set(r["goal"] for r in rows)):
        for cond in ("action", "survey"):
            sub = [r for r in rows if r["goal"] == goal and r["condition"] == cond and r["projection"] is not None]
            if not sub:
                continue
            xm = sum(r["x"] for r in sub if r["x"] is not None) / len(sub)
            pm = sum(r["projection"] for r in sub) / len(sub)
            ps = statistics.stdev([r["projection"] for r in sub]) if len(sub) > 1 else 0.0
            print(f"{goal:22s} {cond:8s} {len(sub):>2d}  {xm:>7.3f} {pm:>+10.4f} {ps:>8.4f}")
    print()

    print("=== Agent-level correlations (across all agents) ===")
    sub = [r for r in rows if r["projection"] is not None and r["x"] is not None]
    xs = [r["x"] for r in sub]
    ps = [r["projection"] for r in sub]
    rho = pearson(ps, xs)
    print(f"  r(projection, X) across all {len(sub)} agents = {rho:+.3f}\n")

    for cond in ("action", "survey"):
        sub_c = [r for r in rows if r["projection"] is not None and r["x"] is not None and r["condition"] == cond]
        if len(sub_c) > 1:
            rho_c = pearson([r["projection"] for r in sub_c], [r["x"] for r in sub_c])
            print(f"  r(projection, X) within {cond} (n={len(sub_c)}) = {rho_c:+.3f}")
    print()

    print("=== Critical test: do A and D differ in projection despite both being X=1? ===")
    a_action = [r["projection"] for r in rows if r["goal"] == "foundation_neutral" and r["condition"] == "action" and r["projection"] is not None]
    d_action = [r["projection"] for r in rows if r["goal"] == "fund_tolerant" and r["condition"] == "action" and r["projection"] is not None]
    if a_action and d_action:
        am = sum(a_action) / len(a_action)
        dm = sum(d_action) / len(d_action)
        ams = statistics.stdev(a_action) if len(a_action) > 1 else 0
        dms = statistics.stdev(d_action) if len(d_action) > 1 else 0
        print(f"  A action (n={len(a_action)}): proj mean = {am:+.4f}  sd = {ams:.4f}")
        print(f"  D action (n={len(d_action)}): proj mean = {dm:+.4f}  sd = {dms:.4f}")
        print(f"  D − A = {dm - am:+.4f}  (positive = D more risk-tolerant in articulated reasoning)")
    print()

    out = {
        "embedder": backend_name,
        "exemplars": {"averse": RISK_AVERSE_EXEMPLARS, "tolerant": RISK_TOLERANT_EXEMPLARS},
        "exemplar_projection": {
            "averse_mean": float(averse_proj.mean()),
            "tolerant_mean": float(tolerant_proj.mean()),
            "separation": float(tolerant_proj.mean() - averse_proj.mean()),
        },
        "rows": rows,
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"[saved] {OUT_PATH}")


if __name__ == "__main__":
    main()
