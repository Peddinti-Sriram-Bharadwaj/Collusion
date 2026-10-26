"""Shared helpers for the pilot-2 analysis steps. Standard library only."""
import glob
import json
import os

PILOT2 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORDS = os.path.join(PILOT2, "records")
PROMPTS = os.path.join(PILOT2, "prompts_verbatim")
OUT = os.path.join(PILOT2, "pilot_analysis", "out")
CONDS = ["C0", "C1", "C2", "C3", "C4"]


def load_records():
    """{(condition, game_number): record dict} for every game in records/."""
    recs = {}
    for path in sorted(glob.glob(os.path.join(RECORDS, "C*_g*.json"))):
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        so = d["scripted_offer"]
        recs[(so["condition"], so["game_number"])] = d
    return recs


def llm_decisions(rec):
    """Challenge decisions made by an LLM agent: not the proposer, not a system auto-challenge, not a fallback."""
    return [d for d in rec["scripted_offer"]["decisions"]
            if not d["challenger_is_scripted"] and not d["is_system"] and not d["is_fallback"]]


def rate(rows):
    """'k/n = p%' for the share of rows where the agent challenged."""
    n = len(rows)
    k = sum(bool(d["was_challenged"]) for d in rows)
    return f"{k}/{n} = {100 * k / n:.0f}%" if n else "0/0 = –"


def ensure_out():
    os.makedirs(OUT, exist_ok=True)
    return OUT
