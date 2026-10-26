"""Freeze the judge v2 validation materials (PREREG Amendment 13; coding_rubric_v3.md section 6).

Ground truth is the intended category fixed when each item was written (`design_SEALED.csv`,
column author_expected_category), as in the v1 procedure; there is no human labelling (PREREG
"Reply classification": human coding is not part of the procedure).

Run once, before any v2 judge call:
    python -I freeze_judge_v2.py
Checks that items.csv, design_SEALED.csv and make_items.py still match the seal hashes recorded in
PREREG Amendment 13; writes validation_set_v2.csv (all 40 items, in the judge script's synthetic-set
format), freeze_report.md and freeze_manifest.json (sha256 of every frozen file); prints the manifest's
own sha256, which is then recorded in PREREG Amendment 13. Refuses to run if a manifest already exists.
"""
import csv
import datetime
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = HERE.parent
PROMPT_V2 = Path(r"X:/Collusion/collusion_hackathon/llm-agent-collusion-2/Collusion_Liars_Bar/analysis/scripted_offer/judge_prompt_v2.txt")
CATEGORIES = ("committed", "rejection", "suspicion-evasive", "other")
SEALED = ("items.csv", "design_SEALED.csv", "make_items.py")


def sha_file(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read(p):
    with open(p, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def main(prereg=RES / "PREREG.md"):
    manifest_path = HERE / "freeze_manifest.json"
    if manifest_path.exists():
        sys.exit("freeze_manifest.json exists: the v2 materials are already frozen")
    text = Path(prereg).read_text(encoding="utf-8")
    unsealed = [n for n in SEALED if sha_file(HERE / n) not in text]
    if unsealed:
        sys.exit(f"not frozen: {unsealed} no longer match the seal hashes recorded in {prereg}")
    items = {r["id"]: r for r in read(HERE / "items.csv")}
    design = {r["id"]: r for r in read(HERE / "design_SEALED.csv")}
    if set(items) != set(design):
        sys.exit("not frozen: items.csv and design_SEALED.csv list different ids")
    bad = [i for i, d in design.items() if d["author_expected_category"] not in CATEGORIES]
    if bad:
        sys.exit(f"not frozen: invalid intended categories for {bad}")
    ids = sorted(items)
    with open(HERE / "validation_set_v2.csv", "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "offer_text", "reply_text", "intended_category", "wary_no_commit", "note"])
        w.writeheader()
        for i in ids:
            cat = design[i]["author_expected_category"]
            w.writerow({"id": i, "offer_text": items[i]["offer_text"], "reply_text": items[i]["reply_text"],
                        "intended_category": cat, "wary_no_commit": int(cat == "suspicion-evasive"),
                        "note": f"{design[i]['message_type']} {design[i]['author_target_type']}"})
    cats = Counter(design[i]["author_expected_category"] for i in ids)
    L = ["# Judge v2 validation set: freeze report", "",
         f"Frozen {datetime.datetime.now(datetime.timezone.utc).isoformat()} (before any v2 judge call).", "",
         f"- Items: {len(ids)}; ground truth = intended category fixed at authoring (sealed in PREREG Amendment 13)",
         f"- Intended categories: {dict(cats)}",
         f"- Zero-tolerance set (intended `suspicion-evasive`): {cats['suspicion-evasive']} items",
         f"- Message types: {dict(Counter(design[i]['message_type'] for i in ids))}", ""]
    (HERE / "freeze_report.md").write_text("\n".join(L), encoding="utf-8")
    frozen = {"coding_rubric_v3.md": RES / "coding_rubric_v3.md", "judge_prompt_v2.txt": PROMPT_V2}
    for n in SEALED + ("validation_set_v2.csv", "freeze_report.md", "freeze_judge_v2.py"):
        frozen[n] = HERE / n
    manifest = {"status": "ok", "n_items": len(ids), "ground_truth": "author_expected_category (sealed)",
                "frozen_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "sha256": {n: sha_file(p) for n, p in frozen.items()},
                "paths": {n: str(p) for n, p in frozen.items()}}
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print("\n".join(L))
    print(f"freeze_manifest.json sha256 = {sha_file(manifest_path)}  (record this in PREREG Amendment 13)")
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
