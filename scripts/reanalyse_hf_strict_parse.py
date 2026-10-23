"""Read saved HF artifacts and write separate strict-parse audit reports.

The input JSON is never modified.  This utility reclassifies only records that
retain ``raw_response`` and reports candidate decisions lacking response text
as not strictly revalidatable.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterator

from src.interpretability.strict_pricing_parser import parse_strict_price_response


AUDIT_SCHEMA = "hf-strict-parse-audit-v1"


def _candidate_records(artifact: dict[str, Any]) -> Iterator[tuple[str, dict[str, Any]]]:
    """Yield decision-shaped records from known HF artifact schemas."""
    if isinstance(artifact.get("decisions"), list):
        for index, record in enumerate(artifact["decisions"]):
            if isinstance(record, dict):
                yield f"decisions[{index}]", record
        return
    if isinstance(artifact.get("trajectories"), dict):
        for variant, trajectory in artifact["trajectories"].items():
            if not isinstance(trajectory, dict):
                continue
            for index, record in enumerate(trajectory.get("decisions", [])):
                if isinstance(record, dict):
                    yield f"trajectories.{variant}.decisions[{index}]", record
        return
    if isinstance(artifact.get("rows"), list):
        for index, row in enumerate(artifact["rows"]):
            if not isinstance(row, dict):
                continue
            record = row.get("record", row)
            if isinstance(record, dict):
                merged = {**row, **record} if record is not row else record
                yield f"rows[{index}]" + (".record" if record is not row else ""), merged
        return
    raise ValueError("Unsupported artifact: no recognized HF decision records.")


def audit_payload(
    artifact: dict[str, Any], *, source_artifact: str, source_payload: bytes, n_prices: int = 10
) -> dict[str, Any]:
    """Reclassify already-read artifact content without mutating it."""
    records = []
    for json_path, record in _candidate_records(artifact):
        response = record.get("raw_response")
        revalidatable = isinstance(response, str)
        parsed = (
            parse_strict_price_response(response, n_prices).to_dict()
            if revalidatable else {
                "selected_price_index": None,
                "analysis_eligible": False,
                "parse_status": "raw_response_unavailable",
            }
        )
        records.append({
            "json_path": json_path,
            "strict_revalidatable": revalidatable,
            "protocol_identity": record.get("protocol", record.get("prompt_format")),
            "model_id": record.get("model_id"),
            "model_revision": record.get("model_revision"),
            "tokenizer_revision": record.get("tokenizer_revision"),
            "episode_id": record.get("episode_id"),
            "scenario_id": record.get("scenario_id"),
            "agent_id": record.get("agent_id"),
            "round_id": record.get("round_id"),
            "original_selected_price_index": record.get("selected_price_index", record.get("proposed_action_index")),
            "original_parse_valid": record.get("parse_valid"),
            "raw_response_sha256": sha256(response.encode("utf-8")).hexdigest() if revalidatable else None,
            **parsed,
        })
    statuses = Counter(record["parse_status"] for record in records)
    revalidatable = [record for record in records if record["strict_revalidatable"]]
    eligible = [record for record in records if record["analysis_eligible"]]
    return {
        "schema_version": AUDIT_SCHEMA,
        "source_artifact": source_artifact,
        "source_artifact_sha256": sha256(source_payload).hexdigest(),
        "source_schema_version": artifact.get("schema_version"),
        "n_prices": n_prices,
        "source_modified": False,
        "summary": {
            "candidate_records": len(records),
            "strict_revalidatable_records": len(revalidatable),
            "records_without_raw_response": len(records) - len(revalidatable),
            "strict_analysis_eligible_records": len(eligible),
            "strict_ineligible_records": len(records) - len(eligible),
            "parse_status_counts": dict(sorted(statuses.items())),
        },
        "records": records,
    }


def audit_artifact(path: str | Path, *, n_prices: int = 10) -> dict[str, Any]:
    """Read and reclassify saved response text without changing the source."""
    source = Path(path)
    payload = source.read_bytes()
    return audit_payload(
        json.loads(payload), source_artifact=str(source), source_payload=payload, n_prices=n_prices
    )


def write_audit_report(report: dict[str, Any], output_dir: str | Path) -> Path:
    """Write a new versioned report, never replacing the source artifact."""
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    source = Path(str(report["source_artifact"]))
    target = directory / f"{source.stem}.strict-parse-audit-v1.json"
    target.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", nargs="+", required=True, help="Saved JSON artifact(s) to read.")
    parser.add_argument("--output-dir", default="artifacts/interpretability/audits")
    parser.add_argument("--n-prices", type=int, default=10)
    args = parser.parse_args()
    for input_path in args.input:
        report = audit_artifact(input_path, n_prices=args.n_prices)
        print(write_audit_report(report, args.output_dir))


if __name__ == "__main__":
    main()
