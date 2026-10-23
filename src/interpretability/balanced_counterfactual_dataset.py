"""Small, pre-split counterfactual dataset protocol; collection is opt-in."""
from __future__ import annotations
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Sequence
import numpy as np
from src.env import LogitBertrandEnv
from src.llm_agent import LLMPricingAgent
from .activation_extractor import HFActivationExtractor
from .matched_prompt_counterfactual import run_matched_prompt_counterfactuals


@dataclass(frozen=True)
class MarketHistoryScenario:
    scenario_id: str
    scenario_seed: int
    split: str
    control_history: tuple[tuple[np.ndarray, np.ndarray], ...]
    undercut_history: tuple[tuple[np.ndarray, np.ndarray], ...]
    intervention: dict[str, Any]


def scenario_split(scenario_id: str, seed: int = 0) -> str:
    """Stable scenario-level split, assigned before any model collection."""
    # Every block of six has one test and one validation scenario; this keeps
    # 10–20 scenario pilots approximately 2/3 train, 1/6 validation, 1/6 test.
    index = int(scenario_id.rsplit("-", 1)[-1])
    bucket = (index + seed) % 6
    return "test" if bucket == 0 else "validation" if bucket == 1 else "train"


def generate_balanced_scenarios(n_scenarios: int = 12, seed: int = 0, history_rounds: int = 2) -> list[MarketHistoryScenario]:
    """Generate valid market histories with a final, strictly lower rival price."""
    if not 10 <= n_scenarios <= 20 or history_rounds < 1:
        raise ValueError("Use 10–20 scenarios and at least one history round.")
    env = LogitBertrandEnv(n_agents=2, n_prices=10)
    scenarios = []
    for index in range(n_scenarios):
        scenario_seed = seed + index
        rng = np.random.default_rng(scenario_seed)
        actions = rng.integers(0, env.n_prices, size=(history_rounds, 2))
        # Balance terminal rival proposals across nonzero grid indices and force
        # a valid lower executed undercut.
        rival_index = 1 + (index % (env.n_prices - 1))
        undercut_index = int(rng.integers(0, rival_index))
        own_index = int((2 * index + 3) % env.n_prices)
        actions[-1] = (rival_index, own_index)
        control, undercut = [], []
        for round_actions in actions:
            prices = env.price_grid[round_actions]
            control.append((prices.copy(), env._profits(prices)))
        undercut_prices = env.price_grid[np.array([undercut_index, own_index])]
        undercut = control[:-1] + [(undercut_prices.copy(), env._profits(undercut_prices))]
        scenario_id = f"scenario-{index:03d}"
        scenarios.append(MarketHistoryScenario(
            scenario_id, scenario_seed, scenario_split(scenario_id, seed), tuple(control), tuple(undercut),
            {"round_id": history_rounds - 1, "target_agent_id": 0, "proposed_action_index": rival_index,
             "executed_action_index": undercut_index, "kind": "market_consistent_undercut"},
        ))
    return scenarios


def _context(scenario: MarketHistoryScenario, history: Sequence[tuple[np.ndarray, np.ndarray]], env: LogitBertrandEnv) -> dict[str, Any]:
    prompt = LLMPricingAgent(1, env, persona=None, seed=0)._build_prompt(list(history), len(history), len(history) + 1)
    return {"prompt": prompt, "full_prompt_hash": sha256(prompt.encode()).hexdigest(), "n_prices": env.n_prices,
            "market_seed": 0, "n_rounds": len(history) + 1, "episode_id": scenario.scenario_id,
            "round_id": len(history), "generation_seed": None}


def _behavioural_history_features(history: Sequence[tuple[np.ndarray, np.ndarray]]) -> list[dict[str, float]]:
    """Numeric baseline containing only fields shown to Agent 1 in its prompt."""
    return [{"own_price": float(prices[1]), "own_profit": float(profits[1]), "rival_price": float(prices[0])}
            for prices, profits in history]


def collect_balanced_counterfactual_dataset(extractor: HFActivationExtractor, scenarios: Sequence[MarketHistoryScenario], *, selected_layers: Sequence[int] | None = None, negative_every: int = 3) -> dict[str, Any]:
    """Opt-in model collection. Synthetic C/D never update market histories."""
    env = LogitBertrandEnv(n_agents=2, n_prices=10)
    rows = []
    for i, scenario in enumerate(scenarios):
        control, undercut = _context(scenario, scenario.control_history, env), _context(scenario, scenario.undercut_history, env)
        control_features, undercut_features = _behavioural_history_features(scenario.control_history), _behavioural_history_features(scenario.undercut_history)
        result = run_matched_prompt_counterfactuals(extractor, control_context=control, undercut_context=undercut, selected_layers=selected_layers)
        names = ["A_original_control", "B_actual_market_undercut", "C_synthetic_rival_price_only", "D_synthetic_own_profit_only"]
        if i % negative_every == 0: names.append("negative_identical_control")
        baseline = result["conditions"]["A_original_control"]
        interaction = {}
        for layer in baseline["layer_vectors"]:
            a,b,c,d = (np.asarray(result["conditions"][name]["layer_vectors"][layer]) for name in names[:4])
            vector = b - c - d + a
            interaction[layer] = {"vector": vector, "norm": float(np.linalg.norm(vector))}
        for name in names:
            record = result["conditions"][name]
            action = record["selected_action_index"]
            features = control_features if name in ("A_original_control", "negative_identical_control") else undercut_features
            if name == "C_synthetic_rival_price_only":
                features = [*control_features[:-1], {**control_features[-1], "rival_price": undercut_features[-1]["rival_price"]}]
            elif name == "D_synthetic_own_profit_only":
                features = [*control_features[:-1], {**control_features[-1], "own_profit": undercut_features[-1]["own_profit"]}]
            rows.append({"scenario_id": scenario.scenario_id, "split": scenario.split, "intervention": scenario.intervention,
                         "condition": name, "record": record, "action_change_from_A": action - baseline["selected_action_index"],
                         "price_response_magnitude": float(env.price_grid[action] - env.price_grid[baseline["selected_action_index"]]),
                         "behavioural_history_only": features, "interaction_B_minus_C_minus_D_plus_A": interaction})
    return {"schema_version": "hf-balanced-counterfactual-dataset-v1", "scenarios": [s.__dict__ for s in scenarios], "rows": rows,
            "split_unit": "scenario_id", "class_balance": class_balance_report(rows),
            "interpretation_scope": "Representation differences are descriptive, not collusion or mechanism evidence."}


def class_balance_report(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    actions = [r["record"]["selected_action_index"] for r in rows if r["condition"] == "A_original_control"]
    changed = [bool(r["action_change_from_A"]) for r in rows if r["condition"] == "B_actual_market_undercut"]
    counts = {str(a): actions.count(a) for a in sorted(set(actions))}
    return {"baseline_action_counts": counts, "undercut_action_changes": sum(changed), "undercut_action_unchanged": len(changed)-sum(changed),
            "predictive_analysis_ready": len(counts) > 1 and sum(changed) >= 4 and len(changed)-sum(changed) >= 4}


def assert_no_split_leakage(rows: Sequence[dict[str, Any]]) -> None:
    seen: dict[str, str] = {}
    for row in rows:
        prior = seen.setdefault(row["scenario_id"], row["split"])
        if prior != row["split"]: raise ValueError("Scenario appears in multiple evaluation splits.")
