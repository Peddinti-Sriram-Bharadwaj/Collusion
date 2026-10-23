"""Regression tests for strict HF-only pricing response parsing."""
from __future__ import annotations

import json
from unittest.mock import patch

from scripts.reanalyse_hf_strict_parse import audit_payload, write_audit_report
from src.interpretability.strict_pricing_parser import parse_strict_price_response


def test_observed_instruction_echo_is_not_a_pricing_decision():
    echo = '''The output should be formatted like so:

{
  "price_index": 3
}
This problem involves understanding and applying concepts related to supply and demand curves,'''
    parsed = parse_strict_price_response(echo, 10)
    assert parsed.selected_price_index is None
    assert parsed.analysis_eligible is False
    assert parsed.parse_status == "extra_text_or_embedded_json"


def test_standalone_chat_json_is_eligible():
    parsed = parse_strict_price_response('{"price_index": 5}', 10)
    assert parsed.selected_price_index == 5
    assert parsed.analysis_eligible is True
    assert parsed.parse_status == "standalone_json"


def test_strict_parser_rejects_malformed_conflicting_extra_boolean_and_out_of_range():
    cases = {
        '{"price_index":': "malformed_json",
        '{"price_index": 2} {"price_index": 3}': "multiple_json_objects",
        '{"price_index": 2, "reason": "extra"}': "wrong_json_schema",
        '{"price_index": true}': "non_integer_price_index",
        '{"price_index": 10}': "out_of_range_price_index",
        '```json\n{"price_index": 2}\n```': "code_fence_or_markdown",
    }
    for response, status in cases.items():
        parsed = parse_strict_price_response(response, 10)
        assert parsed.selected_price_index is None
        assert parsed.analysis_eligible is False
        assert parsed.parse_status == status


def test_reanalysis_writes_separate_report_and_marks_missing_raw_text():
    original = {
        "schema_version": "test-v1",
        "rows": [
            {"scenario_id": "echo", "protocol": "raw", "raw_response": 'prefix {"price_index": 3}'},
            {"scenario_id": "chat", "protocol": "chat", "raw_response": '{"price_index": 4}'},
            {"scenario_id": "missing", "protocol": "raw", "selected_price_index": 2},
        ],
    }
    source_payload = json.dumps(original).encode("utf-8")
    report = audit_payload(original, source_artifact="source.json", source_payload=source_payload)
    assert report["source_modified"] is False
    assert report["summary"] == {
        "candidate_records": 3,
        "strict_revalidatable_records": 2,
        "records_without_raw_response": 1,
        "strict_analysis_eligible_records": 1,
        "strict_ineligible_records": 2,
        "parse_status_counts": {
            "extra_text_or_embedded_json": 1,
            "raw_response_unavailable": 1,
            "standalone_json": 1,
        },
    }
    with patch("scripts.reanalyse_hf_strict_parse.Path.mkdir") as mkdir, patch(
        "scripts.reanalyse_hf_strict_parse.Path.write_text"
    ) as write_text:
        output = write_audit_report(report, "audits")
    assert str(output).endswith("source.strict-parse-audit-v1.json")
    mkdir.assert_called_once()
    write_text.assert_called_once()
