from pathlib import Path

import importlib.util


def _load_sdlc_module():
    path = Path("tools/sdlc/sdlc.py")
    spec = importlib.util.spec_from_file_location("sdlc_tool_gate_input_tests", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_build_gate_inputs_sanitizes_readiness_state(tmp_path) -> None:
    sdlc = _load_sdlc_module()

    root = tmp_path
    sdlc.ROOT = root
    sdlc.SDLC = root / "sdlc"
    sdlc.PLANS = sdlc.SDLC / "plans"
    sdlc.PLAN_DIFFS = sdlc.PLANS / "diffs"
    sdlc.CONTEXT = sdlc.SDLC / "context"
    sdlc.QA = sdlc.SDLC / "qa"
    sdlc.EVAL_RESULTS = sdlc.SDLC / "eval_results"
    sdlc.SNAPSHOTS = sdlc.SDLC / "snapshots"
    sdlc.GATE_INPUTS = sdlc.SDLC / "gate_inputs"
    sdlc.EVALS = root / "evals"
    sdlc.STATE = sdlc.SDLC / "state.json"
    sdlc.CONSTRAINTS = sdlc.SDLC / "constraints.json"
    sdlc.SUBAGENTS = sdlc.SDLC / "subagents.yaml"
    sdlc.GRYPH_EVENTS = sdlc.SDLC / "gryph_events.jsonl"
    sdlc.GRYPH_SUMMARY = sdlc.SDLC / "gryph_summary.json"
    sdlc.EVAL_POLICY = sdlc.SDLC / "eval_policy.json"

    sdlc.PLANS.mkdir(parents=True)
    sdlc.CONTEXT.mkdir(parents=True)
    sdlc.QA.mkdir(parents=True)
    sdlc.EVALS.mkdir(parents=True)

    sdlc.write_json(
        sdlc.STATE,
        {
            "current_phase": "review",
            "implementation_allowed": False,
            "blocked_reasons": ["implementation readiness eval has not passed"],
            "active_feature": "existing-project-sdlc-baseline",
        },
    )
    sdlc.write_json(
        sdlc.CONSTRAINTS,
        {
            "active": [{"id": "C001", "source": "test", "text": "Synthetic only."}],
            "non_negotiable": ["C001"],
        },
    )
    (sdlc.PLANS / "accepted_plan.md").write_text("# Plan\n\nConcrete plan.", encoding="utf-8")
    sdlc.write_json(
        sdlc.QA / "acceptance_criteria.json",
        {"criteria": [{"id": "A001", "text": "Has acceptance criteria."}]},
    )
    (sdlc.QA / "test_strategy.md").write_text("# Test Strategy\n\nConcrete tests.", encoding="utf-8")
    sdlc.SUBAGENTS.write_text("models:\n  gpt-5.4:\n    role: reviewer\n", encoding="utf-8")
    (sdlc.CONTEXT / "dynamic_context.md").write_text("# Dynamic Context\n\nGenerated.", encoding="utf-8")
    sdlc.write_json(sdlc.GRYPH_SUMMARY, {"event_count": 0})

    sdlc.build_gate_inputs("readiness")

    readiness_state = sdlc.read_json(sdlc.GATE_INPUTS / "readiness_state.json", {})

    assert readiness_state == {
        "active_feature": "existing-project-sdlc-baseline",
        "required_artifacts": {
            "accepted_plan_exists": True,
            "constraints_exist": True,
            "acceptance_criteria_exist": True,
            "test_strategy_exists": True,
            "subagents_exist": True,
        },
    }


def test_write_eval_templates_strengthens_plan_and_readiness_prompts(tmp_path) -> None:
    sdlc = _load_sdlc_module()

    sdlc.ROOT = tmp_path
    sdlc.EVALS = tmp_path / "evals"
    sdlc.EVALS.mkdir(parents=True)

    sdlc.write_eval_templates()

    plan_text = (sdlc.EVALS / "plan_constraints.promptfoo.yaml").read_text(encoding="utf-8")
    readiness_text = (sdlc.EVALS / "implementation_readiness.promptfoo.yaml").read_text(encoding="utf-8")

    assert "Treat paraphrases and semantic equivalents as preserved constraints." in plan_text
    assert "If the previous plan and candidate plan are identical or materially identical" in plan_text
    assert "Evaluate readiness from artifact completeness and concreteness only." in readiness_text
    assert "Do not use the governor's current phase or blocked status as a reason to" in readiness_text


def test_identical_plan_gate_is_deterministic_and_skips_promptfoo(tmp_path, monkeypatch) -> None:
    sdlc = _load_sdlc_module()

    root = tmp_path
    sdlc.ROOT = root
    sdlc.SDLC = root / "sdlc"
    sdlc.PLANS = sdlc.SDLC / "plans"
    sdlc.PLAN_DIFFS = sdlc.PLANS / "diffs"
    sdlc.CONTEXT = sdlc.SDLC / "context"
    sdlc.QA = sdlc.SDLC / "qa"
    sdlc.EVAL_RESULTS = sdlc.SDLC / "eval_results"
    sdlc.SNAPSHOTS = sdlc.SDLC / "snapshots"
    sdlc.GATE_INPUTS = sdlc.SDLC / "gate_inputs"
    sdlc.EVALS = root / "evals"
    sdlc.STATE = sdlc.SDLC / "state.json"
    sdlc.CONSTRAINTS = sdlc.SDLC / "constraints.json"
    sdlc.SUBAGENTS = sdlc.SDLC / "subagents.yaml"
    sdlc.GRYPH_EVENTS = sdlc.SDLC / "gryph_events.jsonl"
    sdlc.GRYPH_SUMMARY = sdlc.SDLC / "gryph_summary.json"
    sdlc.EVAL_POLICY = sdlc.SDLC / "eval_policy.json"

    sdlc.PLANS.mkdir(parents=True)
    sdlc.CONTEXT.mkdir(parents=True)
    sdlc.QA.mkdir(parents=True)
    sdlc.EVALS.mkdir(parents=True)
    sdlc.EVAL_RESULTS.mkdir(parents=True)

    sdlc.write_json(sdlc.STATE, sdlc.DEFAULT_STATE)
    sdlc.write_json(
        sdlc.CONSTRAINTS,
        {"active": [{"id": "C001", "source": "test", "text": "Synthetic only."}], "non_negotiable": ["C001"]},
    )
    (sdlc.PLANS / "accepted_plan.md").write_text("# Plan\n\nSame plan.", encoding="utf-8")
    sdlc.write_json(sdlc.QA / "acceptance_criteria.json", {"criteria": [{"id": "A001", "text": "Concrete"}]})
    (sdlc.QA / "test_strategy.md").write_text("# Test Strategy\n\nConcrete.", encoding="utf-8")
    sdlc.SUBAGENTS.write_text("models:\n  gpt-5.4:\n    role: reviewer\n", encoding="utf-8")
    (sdlc.CONTEXT / "dynamic_context.md").write_text("# Dynamic Context\n\nGenerated.", encoding="utf-8")
    sdlc.write_json(sdlc.GRYPH_SUMMARY, {"event_count": 0})
    sdlc.write_json(
        sdlc.EVAL_POLICY,
        {
            "approved_for_sdlc_gate_inputs": True,
            "approved_models": ["llama-3.1-8b-instant"],
            "allowed_files": [
                "sdlc/gate_inputs/plan_constraints.json",
                "sdlc/gate_inputs/previous_plan.md",
                "sdlc/gate_inputs/candidate_plan.md",
            ],
            "never_send": [],
        },
    )
    sdlc.write_eval_templates()

    def _forbidden_subprocess_run(*args, **kwargs):
        raise AssertionError("promptfoo should not run for identical plans")

    monkeypatch.setattr(sdlc.subprocess, "run", _forbidden_subprocess_run)

    exit_code = sdlc.run_eval(type("Args", (), {"kind": "plan"})())
    result = sdlc.read_json(sdlc.EVAL_RESULTS / "plan.latest.json", {})

    assert exit_code == 0
    assert result["passed"] is True
    assert result["exit_code"] == 0
    assert "deterministic" in result["stdout"].lower()


def test_readiness_gate_can_pass_deterministically_for_concrete_artifacts(tmp_path, monkeypatch) -> None:
    sdlc = _load_sdlc_module()

    root = tmp_path
    sdlc.ROOT = root
    sdlc.SDLC = root / "sdlc"
    sdlc.PLANS = sdlc.SDLC / "plans"
    sdlc.PLAN_DIFFS = sdlc.PLANS / "diffs"
    sdlc.CONTEXT = sdlc.SDLC / "context"
    sdlc.QA = sdlc.SDLC / "qa"
    sdlc.EVAL_RESULTS = sdlc.SDLC / "eval_results"
    sdlc.SNAPSHOTS = sdlc.SDLC / "snapshots"
    sdlc.GATE_INPUTS = sdlc.SDLC / "gate_inputs"
    sdlc.EVALS = root / "evals"
    sdlc.STATE = sdlc.SDLC / "state.json"
    sdlc.CONSTRAINTS = sdlc.SDLC / "constraints.json"
    sdlc.SUBAGENTS = sdlc.SDLC / "subagents.yaml"
    sdlc.GRYPH_EVENTS = sdlc.SDLC / "gryph_events.jsonl"
    sdlc.GRYPH_SUMMARY = sdlc.SDLC / "gryph_summary.json"
    sdlc.EVAL_POLICY = sdlc.SDLC / "eval_policy.json"

    sdlc.PLANS.mkdir(parents=True)
    sdlc.CONTEXT.mkdir(parents=True)
    sdlc.QA.mkdir(parents=True)
    sdlc.EVALS.mkdir(parents=True)
    sdlc.EVAL_RESULTS.mkdir(parents=True)

    sdlc.write_json(sdlc.STATE, sdlc.DEFAULT_STATE)
    sdlc.write_json(
        sdlc.CONSTRAINTS,
        {"active": [{"id": "C001", "source": "test", "text": "Synthetic only."}], "non_negotiable": ["C001"]},
    )
    (sdlc.PLANS / "accepted_plan.md").write_text(
        "# Accepted Plan\n\n## Product\nConcrete scope.\n\n## Architecture\nConcrete bounded architecture.\n",
        encoding="utf-8",
    )
    sdlc.write_json(
        sdlc.QA / "acceptance_criteria.json",
        {"criteria": [{"id": "A001", "text": "Concrete acceptance criteria."}]},
    )
    (sdlc.QA / "test_strategy.md").write_text(
        "# Test Strategy\n\n- Run unit tests\n- Run integration tests\n",
        encoding="utf-8",
    )
    sdlc.SUBAGENTS.write_text(
        "models:\n  gpt-5.4:\n    role: reviewer\n  gpt-5.4-mini:\n    role: implementer\n",
        encoding="utf-8",
    )
    (sdlc.CONTEXT / "dynamic_context.md").write_text("# Dynamic Context\n\nGenerated.", encoding="utf-8")
    sdlc.write_json(sdlc.GRYPH_SUMMARY, {"event_count": 0})
    sdlc.write_json(
        sdlc.EVAL_POLICY,
        {
            "approved_for_sdlc_gate_inputs": True,
            "approved_models": ["llama-3.1-8b-instant"],
            "allowed_files": [
                "sdlc/gate_inputs/readiness_state.json",
                "sdlc/gate_inputs/readiness_plan.md",
                "sdlc/gate_inputs/readiness_acceptance.json",
                "sdlc/gate_inputs/readiness_test_strategy.md",
                "sdlc/gate_inputs/readiness_subagents.md",
            ],
            "never_send": [],
        },
    )
    sdlc.write_eval_templates()

    def _forbidden_subprocess_run(*args, **kwargs):
        raise AssertionError("promptfoo should not run for concrete readiness artifacts")

    monkeypatch.setattr(sdlc.subprocess, "run", _forbidden_subprocess_run)

    exit_code = sdlc.run_eval(type("Args", (), {"kind": "readiness"})())
    result = sdlc.read_json(sdlc.EVAL_RESULTS / "readiness.latest.json", {})

    assert exit_code == 0
    assert result["passed"] is True
    assert result["exit_code"] == 0
    assert "artifact readiness checks passed" in result["stdout"].lower()
