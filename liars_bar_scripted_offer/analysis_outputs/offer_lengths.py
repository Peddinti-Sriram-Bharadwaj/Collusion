"""Offer message lengths: words / characters for C1-C3 and C5 (v6 wording), and the prompt tokens of the
offer-response calls in pilot 2 (C1-C3 only; C5 was not run), per model.

Token counts come from the server's own usage numbers: in pilot 2 (serial, 0 API errors) the k-th
"LLM Request" line of a game's log is the k-th usage row of that game, so the offer-response calls
(prompts asking for "decision") can be matched to their prompt_tokens. Differences between
conditions within a model reflect the message text (the rest of the prompt is the same template
apart from the agent's name).

Usage: python -I offer_lengths.py <game_dir> <pilot2_records_dir> <out_md>
"""
import json
import re
import statistics
import sys
from collections import defaultdict
from pathlib import Path

game_dir, rec_dir, out_md = map(Path, sys.argv[1:4])
FILES = {"C1": "offer_direct.txt", "C1b": "offer_broker.txt", "C2": "offer_hint.txt", "C3": "offer_benign.txt",
         "C5": "offer_placebo.txt"}

rows = []
for c, f in FILES.items():
    text = (game_dir / "prompts" / "scripted_offer" / f).read_text(encoding="utf-8")
    quoted = text.split("\n", 1)[1].strip()          # the message itself, without the header line
    rows.append((c, f, len(quoted.replace("{agent_name}", "Luke").split()), len(quoted.replace("{agent_name}", "Luke"))))

usage = [json.loads(l) for l in (rec_dir / "usage.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
by_game = defaultdict(list)
for u in usage:
    by_game[(u["condition"], u["game_number"])].append(u)
tokens = defaultdict(list)
mismatch = []
for (c, g), us in by_game.items():
    log = (rec_dir / "logs" / f"{c}_g{g:02d}.log").read_text(encoding="utf-8")
    reqs = [l for l in log.splitlines() if l.startswith("LLM Request to ")]
    if len(reqs) != len(us):
        mismatch.append((c, g, len(reqs), len(us)))
        continue
    for line, u in zip(reqs, us):
        if c in FILES and '\\"decision\\"' in line or (c in FILES and '"decision"' in line):
            model = line[len("LLM Request to "):].split(":", 1)[0]
            tokens[(c, model)].append(u["prompt_tokens"])

L = ["# Offer message lengths (v7 wording: C1, C1b, C2, C3, C5)", "",
     "Sprint work, 2026-10-25 (v7: C1b added, C3 replaced). Message = the quoted text after the 'Private message from ...' header line, with "
     "{agent_name} = Luke and {proposer_name} = Riley. The header line is identical in all five files.", "",
     "| cond | file | words | characters |", "|---|---|---|---|"]
for c, f, w, ch in rows:
    L.append(f"| {c} | {f} | {w} | {ch} |")
L += ["", "Prompt tokens of the offer-response call in pilot 2 (server usage, median over calls). NOTE: pilot 2 used the "
      "v5 wordings of C2 and C3 (see pilot2/prompts_verbatim/), so these are token counts of the OLD C2/C3 messages; C1 "
      "is unchanged. C1b and C5 were not run in pilot 2; no token count is available for them without the models' tokenizers.", "",
      "| model | C1 | C2 | C3 |", "|---|---|---|---|"]
for model in sorted({m for _, m in tokens}):
    cells = []
    for c in ("C1", "C2", "C3"):
        v = tokens.get((c, model), [])
        cells.append(f"{statistics.median(v):.0f} (n={len(v)})" if v else "n/a")
    L.append(f"| {model} | " + " | ".join(cells) + " |")
if mismatch:
    L += ["", f"Games skipped because log requests and usage rows did not align: {mismatch}"]
w = {c: wc for c, _, wc, _ in rows}
L += ["", f"Reading: v7 word counts are C1 {w['C1']}, C1b {w['C1b']}, C2 {w['C2']}, C3 {w['C3']}, C5 {w['C5']} (range {min(w.values())}-"
      f"{max(w.values())}); lengths are comparable but not identical. In pilot 2 the (v5) C1-C3 offer prompts differed "
      "by at most about 12 tokens per model."]
out_md.write_text("\n".join(L) + "\n", encoding="utf-8")
print("\n".join(L))
