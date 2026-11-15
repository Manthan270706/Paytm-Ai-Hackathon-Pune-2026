import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.tests.eval.harness import EvalHarness
from app.tests.eval.scenarios import BENCHMARK_SCENARIOS, EvalScenario


@pytest.fixture
def eval_client() -> TestClient:
    return TestClient(app)


def test_eval_harness_settlement_scenario(eval_client: TestClient) -> None:
    harness = EvalHarness(client=eval_client)
    harness.reset_demo_state()

    settlement_scenario = BENCHMARK_SCENARIOS[0]  # SETTLE-EN-01
    result = harness.evaluate_scenario(settlement_scenario)

    assert result.passed is True
    assert result.intent_match is True
    assert result.zero_float_money is True
    assert result.number_grounding is True
    assert result.no_forbidden_tokens is True


def test_eval_harness_adversarial_injection(eval_client: TestClient) -> None:
    harness = EvalHarness(client=eval_client)
    harness.reset_demo_state()

    adv_scenario = next(s for s in BENCHMARK_SCENARIOS if s.id == "ADV-INJECT-01")
    result = harness.evaluate_scenario(adv_scenario)

    assert result.passed is True
    assert result.refusal_satisfied is True
    assert result.no_forbidden_tokens is True


def test_eval_harness_card_redaction(eval_client: TestClient) -> None:
    harness = EvalHarness(client=eval_client)
    harness.reset_demo_state()

    leak_scenario = next(s for s in BENCHMARK_SCENARIOS if s.id == "ADV-CRED-LEAK-04")
    result = harness.evaluate_scenario(leak_scenario)

    assert result.passed is True
    assert result.refusal_satisfied is True
    assert "4111222233334444" not in result.reply_excerpt
