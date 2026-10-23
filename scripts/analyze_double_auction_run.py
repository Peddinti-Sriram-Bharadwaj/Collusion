"""Analyze a completed llm-agent-collusion (double auction) run directory:
primary endpoint (their own collusion_auc / avg seller-ask index) plus our
own secondary endpoint (rate of COLLUSION_KEYWORDS-flagged seller messages),
for the RQ 3.4 Modal-replication plan (see rq34_surveillance_modal_plan.md).

Usage:
    python3 scripts/analyze_double_auction_run.py <path-to-results-tag-dir>
"""
import json
import re
import sys
from pathlib import Path

from src.llm_agent import _contains_collusive_language


def analyze_run(run_dir: Path) -> dict:
    metrics_path = run_dir / "collusion_metrics.json"
    if not metrics_path.exists():
        raise FileNotFoundError(f"no collusion_metrics.json in {run_dir}")
    metrics = json.loads(metrics_path.read_text())

    messages = []
    for md_path in run_dir.glob("Seller *.md"):
        text = md_path.read_text()
        for m in re.finditer(r'"message_to_sellers"\s*:\s*"((?:[^"\\]|\\.)*)"', text):
            msg = m.group(1).strip()
            if msg and msg.lower() not in ("null", "no message to sellers.", "none"):
                messages.append(msg)

    n_flagged = sum(1 for m in messages if _contains_collusive_language(m))

    return {
        "run_dir": str(run_dir),
        "collusion_auc": metrics.get("collusion_auc"),
        "collusion_indices_avg_seller_asks": metrics.get("collusion_indices_avg_seller_asks"),
        "avg_seller_asks_by_round": metrics.get("avg_seller_asks_by_round"),
        "n_messages": len(messages),
        "n_flagged": n_flagged,
        "flagged_rate": (n_flagged / len(messages)) if messages else None,
        "sample_flagged_messages": [m for m in messages if _contains_collusive_language(m)][:5],
    }


if __name__ == "__main__":
    run_dir = Path(sys.argv[1])
    result = analyze_run(run_dir)
    print(json.dumps(result, indent=2))
