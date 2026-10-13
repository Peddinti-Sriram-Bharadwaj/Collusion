import numpy as np
import pytest

from src.env import LogitBertrandEnv
from src.llm_agent import (
    LLMPricingAgent,
    LLMChatPricingAgent,
    _FixedPlantAgent,
    run_llm_episode,
    check_ollama_available,
    OllamaUnavailableError,
    ANTITRUST_WARNING,
)


def _make_agent():
    env = LogitBertrandEnv(n_agents=2, n_prices=10)
    return LLMPricingAgent(agent_id=0, env=env, seed=0), env


def test_parse_index_well_formed_json():
    agent, env = _make_agent()
    idx = agent._parse_index('{"price_index": 3}')
    assert idx == 3


def test_parse_index_json_with_surrounding_text():
    agent, env = _make_agent()
    idx = agent._parse_index('Sure, here is my choice: {"price_index": 7} -- I think this maximizes profit.')
    assert idx == 7


def test_parse_index_out_of_range_falls_back_to_random():
    agent, env = _make_agent()
    idx = agent._parse_index('{"price_index": 999}')
    assert 0 <= idx < env.n_prices


def test_parse_index_no_json_falls_back_to_bare_number():
    agent, env = _make_agent()
    idx = agent._parse_index("I'll go with 5.")
    assert idx == 5


def test_parse_index_garbage_falls_back_to_random_in_range():
    agent, env = _make_agent()
    idx = agent._parse_index("I refuse to play this game.")
    assert 0 <= idx < env.n_prices


def test_build_prompt_includes_grid_and_round_info():
    agent, env = _make_agent()
    prompt = agent._build_prompt(history=[], round_num=0, n_rounds=30)
    assert "round 1 of 30" in prompt
    assert "no history yet" in prompt
    for i, p in enumerate(env.price_grid):
        assert f"{i}:${p:.2f}" in prompt


def test_build_prompt_includes_recent_history():
    agent, env = _make_agent()
    prices = np.array([1.5, 1.6])
    profits = np.array([0.2, 0.25])
    prompt = agent._build_prompt(history=[(prices, profits)], round_num=1, n_rounds=30)
    assert "Round 0" in prompt
    assert "1.50" in prompt


def test_build_prompt_truncates_to_last_10_rounds():
    agent, env = _make_agent()
    history = [(np.array([1.5, 1.6]), np.array([0.2, 0.25])) for _ in range(20)]
    prompt = agent._build_prompt(history=history, round_num=20, n_rounds=30)
    assert prompt.count("Round ") == 10


def _make_chat_agent():
    env = LogitBertrandEnv(n_agents=2, n_prices=10)
    return LLMChatPricingAgent(agent_id=0, env=env, seed=0), env


def test_chat_agent_starts_with_one_system_message():
    agent, env = _make_chat_agent()
    assert len(agent.messages) == 1
    assert agent.messages[0]["role"] == "system"
    assert "Firm 0" in agent.messages[0]["content"]


def test_chat_agent_system_prompt_includes_grid():
    agent, env = _make_chat_agent()
    for i, p in enumerate(env.price_grid):
        assert f"{i}:${p:.2f}" in agent.messages[0]["content"]


def test_chat_round_message_first_round_has_no_result():
    agent, env = _make_chat_agent()
    msg = agent._round_user_message(history=[], round_num=0, n_rounds=30)
    assert "Round 1 of 30" in msg
    assert "Result of" not in msg


def test_chat_round_message_later_round_includes_last_result():
    agent, env = _make_chat_agent()
    history = [(np.array([1.5, 1.6]), np.array([0.2, 0.25]))]
    msg = agent._round_user_message(history=history, round_num=1, n_rounds=30)
    assert "Result of round 1" in msg
    assert "1.50" in msg
    assert "round 2 of 30" in msg


def test_chat_agent_parse_index_same_as_stateless():
    agent, env = _make_chat_agent()
    assert agent._parse_index('{"price_index": 3}') == 3
    idx = agent._parse_index("garbage")
    assert 0 <= idx < env.n_prices


def test_fixed_plant_agent_always_returns_same_index_and_never_fails():
    plant = _FixedPlantAgent(action_index=4)
    for _ in range(10):
        idx, failed = plant.act(history=[], round_num=0, n_rounds=30)
        assert idx == 4
        assert failed is False


def test_warning_text_appears_in_stateless_prompt_when_enabled():
    env = LogitBertrandEnv(n_agents=2, n_prices=10)
    agent = LLMPricingAgent(agent_id=0, env=env, warning=True, seed=0)
    prompt = agent._build_prompt(history=[], round_num=0, n_rounds=30)
    assert "antitrust regulator" in prompt.lower()


def test_warning_text_absent_from_stateless_prompt_by_default():
    env = LogitBertrandEnv(n_agents=2, n_prices=10)
    agent = LLMPricingAgent(agent_id=0, env=env, seed=0)
    prompt = agent._build_prompt(history=[], round_num=0, n_rounds=30)
    assert "antitrust regulator" not in prompt.lower()


def test_warning_text_appears_in_chat_system_prompt_when_enabled():
    env = LogitBertrandEnv(n_agents=2, n_prices=10)
    agent = LLMChatPricingAgent(agent_id=0, env=env, warning=True, seed=0)
    assert "antitrust regulator" in agent.messages[0]["content"].lower()


def test_warning_text_absent_from_chat_system_prompt_by_default():
    env = LogitBertrandEnv(n_agents=2, n_prices=10)
    agent = LLMChatPricingAgent(agent_id=0, env=env, seed=0)
    assert "antitrust regulator" not in agent.messages[0]["content"].lower()


class _StubHighPriceAgent:
    """Always proposes the highest grid index -- used to deterministically
    trigger the veto mechanism without any real LLM call."""

    def __init__(self, n_prices: int):
        self.n_prices = n_prices

    def act(self, history, round_num, n_rounds):
        return self.n_prices - 1, False


def test_veto_forces_overpriced_agent_down_to_nash(monkeypatch):
    import src.llm_agent as llm_mod

    # Patch both LLM agent classes so run_llm_episode's internal construction
    # produces our deterministic high-price stub instead of calling Ollama.
    monkeypatch.setattr(llm_mod, "LLMPricingAgent", lambda agent_id, env, model, warning, seed: _StubHighPriceAgent(env.n_prices))

    env = LogitBertrandEnv(n_agents=2, n_prices=10)
    nash_grid_price = env.price_grid[int(np.argmin(np.abs(env.price_grid - env.p_nash)))]

    r = run_llm_episode(n_agents=2, n_prices=10, n_rounds=3, veto=True, veto_margin_fraction=0.3, seed=0)
    assert r["n_vetoes"] > 0
    # every round, both agents attempted the max price and got vetoed to the nearest grid point to Nash
    assert np.allclose(r["price_history"], nash_grid_price, atol=1e-6)


def test_veto_disabled_lets_high_prices_through(monkeypatch):
    import src.llm_agent as llm_mod

    monkeypatch.setattr(llm_mod, "LLMPricingAgent", lambda agent_id, env, model, warning, seed: _StubHighPriceAgent(env.n_prices))

    r = run_llm_episode(n_agents=2, n_prices=10, n_rounds=3, veto=False, seed=0)
    assert r["n_vetoes"] == 0
    assert np.all(r["price_history"] == r["price_history"].max())  # stayed at the max grid price, not forced to Nash


def test_check_ollama_available_raises_when_unreachable(monkeypatch):
    import requests

    def fake_get(*args, **kwargs):
        raise requests.exceptions.ConnectionError("refused")

    monkeypatch.setattr(requests, "get", fake_get)
    with pytest.raises(OllamaUnavailableError):
        check_ollama_available()


def test_check_ollama_available_raises_when_model_missing(monkeypatch):
    import requests

    class FakeResp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"models": [{"name": "some-other-model"}]}

    monkeypatch.setattr(requests, "get", lambda *a, **k: FakeResp())
    with pytest.raises(OllamaUnavailableError):
        check_ollama_available(model="qwen2.5:7b-instruct")


def test_run_llm_episode_fails_fast_when_ollama_unreachable(monkeypatch):
    import src.llm_agent as llm_mod

    def fake_check(*args, **kwargs):
        raise OllamaUnavailableError("down")

    monkeypatch.setattr(llm_mod, "check_ollama_available", fake_check)
    with pytest.raises(OllamaUnavailableError):
        run_llm_episode(n_agents=2, n_prices=10, n_rounds=3, seed=0)


def test_run_llm_episode_skips_check_when_all_agents_fixed(monkeypatch):
    import src.llm_agent as llm_mod

    def fake_check(*args, **kwargs):
        raise OllamaUnavailableError("down")

    monkeypatch.setattr(llm_mod, "check_ollama_available", fake_check)
    # all agents fixed -> no real LLM call needed -> should NOT raise
    r = run_llm_episode(n_agents=2, n_prices=10, n_rounds=3, fixed_agent_ids=[0, 1], seed=0)
    assert np.isfinite(r["delta"])


def test_veto_exempts_fixed_plant_agents(monkeypatch):
    import src.llm_agent as llm_mod

    monkeypatch.setattr(llm_mod, "LLMPricingAgent", lambda agent_id, env, model, warning, seed: _StubHighPriceAgent(env.n_prices))

    r = run_llm_episode(n_agents=2, n_prices=10, n_rounds=2, fixed_agent_ids=[1], veto=True, seed=0)
    # agent 1 is the fixed plant (pinned at Nash already); only agent 0's high
    # price should ever get vetoed, so n_vetoes should be <= n_rounds, not 2x
    assert r["n_vetoes"] <= 2
