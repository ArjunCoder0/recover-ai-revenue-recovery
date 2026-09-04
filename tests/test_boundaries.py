"""Architectural boundary tests to guarantee strict safety fences."""

from pathlib import Path


def test_safety_boundary_policy_and_decide_isolation():
    root = Path(__file__).parent.parent / "recover"
    policy_src = (root / "policy.py").read_text(encoding="utf-8")
    decide_src = (root / "decide.py").read_text(encoding="utf-8")

    forbidden_tokens = ["hidden_recovery_prob", "responsiveness"]

    for token in forbidden_tokens:
        assert token not in policy_src, f"Violation: policy.py references hidden token '{token}'"
        assert token not in decide_src, f"Violation: decide.py references hidden token '{token}'"


def test_engine_hidden_probability_calls_bounded():
    engine_path = Path(__file__).parent.parent / "recover" / "engine.py"
    if engine_path.exists():
        src = engine_path.read_text(encoding="utf-8")
        # Allowed at most twice (run execution step + execute_human_action)
        count = src.count("hidden_recovery_prob")
        assert count <= 3, f"engine.py references hidden_recovery_prob {count} times (> 3)"
