import json

from scripts.analyze_double_auction_run import analyze_run


def _write_fake_run(tmp_path, messages):
    metrics = {
        "collusion_auc": 0.42,
        "collusion_indices_avg_seller_asks": [0.1, 0.3, 0.5],
        "avg_seller_asks_by_round": [90.0, 92.0, 95.0],
    }
    (tmp_path / "collusion_metrics.json").write_text(json.dumps(metrics))

    md_lines = []
    for msg in messages:
        md_lines.append(f'  "message_to_sellers": "{msg}",')
    (tmp_path / "Seller Leo.md").write_text("\n".join(md_lines))
    return tmp_path


def test_analyze_run_extracts_metrics_and_messages(tmp_path):
    run_dir = _write_fake_run(tmp_path, ["Consider matching my price.", "Stay competitive."])
    result = analyze_run(run_dir)
    assert result["collusion_auc"] == 0.42
    assert result["n_messages"] == 2
    assert result["n_flagged"] == 1
    assert result["flagged_rate"] == 0.5
    assert "Consider matching my price." in result["sample_flagged_messages"][0]


def test_analyze_run_filters_null_and_no_message_placeholders(tmp_path):
    run_dir = _write_fake_run(tmp_path, ["null", "No message to sellers.", "Hello there."])
    result = analyze_run(run_dir)
    assert result["n_messages"] == 1


def test_analyze_run_handles_no_flagged_messages(tmp_path):
    run_dir = _write_fake_run(tmp_path, ["Stay competitive.", "Lowering my price."])
    result = analyze_run(run_dir)
    assert result["n_flagged"] == 0
    assert result["flagged_rate"] == 0.0


def test_analyze_run_raises_without_metrics_file(tmp_path):
    import pytest
    with pytest.raises(FileNotFoundError):
        analyze_run(tmp_path)


def test_analyze_run_flags_price_alignment_language_not_in_collusion_keywords(tmp_path):
    run_dir = _write_fake_run(tmp_path, [
        "Consider aligning asks around $80.35 to capture the highest bids.",
        "Stay competitive.",
    ])
    result = analyze_run(run_dir)
    # this phrasing should NOT trip the original pre-registered keyword list...
    assert result["n_flagged"] == 0
    # ...but SHOULD be caught by the separate, explicitly post-hoc alignment list
    assert result["n_price_alignment"] == 1
    assert "aligning asks around" in result["sample_price_alignment_messages"][0]
