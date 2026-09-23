import numpy as np

from src.env import LogitBertrandEnv
from src.llm_agent import LLMPricingAgent, _FixedPlantAgent


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


def test_fixed_plant_agent_always_returns_same_index_and_never_fails():
    plant = _FixedPlantAgent(action_index=4)
    for _ in range(10):
        idx, failed = plant.act(history=[], round_num=0, n_rounds=30)
        assert idx == 4
        assert failed is False
