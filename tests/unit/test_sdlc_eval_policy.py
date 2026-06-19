from pathlib import Path

import importlib.util


def _load_sdlc_module():
    path = Path("tools/sdlc/sdlc.py")
    spec = importlib.util.spec_from_file_location("sdlc_tool_for_tests", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_promptfoo_provider_model_parses_groq_openai_compatible_model() -> None:
    sdlc = _load_sdlc_module()

    assert (
        sdlc.promptfoo_provider_model("providers:\n  - id: openai:chat:llama-3.1-8b-instant\n")
        == "llama-3.1-8b-instant"
    )


def test_promptfoo_provider_model_parses_google_model() -> None:
    sdlc = _load_sdlc_module()

    assert sdlc.promptfoo_provider_model("providers:\n  - id: google:gemini-2.5-flash\n") == "gemini-2.5-flash"


def test_eval_environment_accepts_groq_dotenv_alias(tmp_path, monkeypatch) -> None:
    sdlc = _load_sdlc_module()
    monkeypatch.setattr(sdlc, "ROOT", tmp_path)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    (tmp_path / ".env").write_text("groq_api_key=test-key\n", encoding="utf-8")

    env = sdlc.eval_environment()

    assert env["GROQ_API_KEY"] == "test-key"


def test_eval_environment_accepts_gemini_dotenv_alias_and_sets_google_key(tmp_path, monkeypatch) -> None:
    sdlc = _load_sdlc_module()
    monkeypatch.setattr(sdlc, "ROOT", tmp_path)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    (tmp_path / ".env").write_text("gemini_api_key=test-gemini-key\n", encoding="utf-8")

    env = sdlc.eval_environment()

    assert env["GEMINI_API_KEY"] == "test-gemini-key"
    assert env["GOOGLE_API_KEY"] == "test-gemini-key"


def test_provider_chain_is_gemini_then_groq_then_openrouter() -> None:
    sdlc = _load_sdlc_module()

    chain = sdlc.sdlc_provider_chain()

    assert [item["name"] for item in chain] == ["gemini", "groq", "openrouter"]


def test_render_eval_config_with_provider_rewrites_file_refs_to_absolute_paths(tmp_path, monkeypatch) -> None:
    sdlc = _load_sdlc_module()
    monkeypatch.setattr(sdlc, "ROOT", tmp_path)
    monkeypatch.setattr(sdlc, "EVALS", tmp_path / "evals")

    (tmp_path / "evals").mkdir(parents=True, exist_ok=True)
    (tmp_path / "sdlc" / "gate_inputs").mkdir(parents=True, exist_ok=True)
    config_path = tmp_path / "evals" / "final_compliance.promptfoo.yaml"
    config_path.write_text(
        "\n".join(
            [
                "description: Final compliance gate",
                "providers:",
                "  - id: google:gemini-2.5-flash",
                "    config:",
                "      apiKey: '{{ env.GEMINI_API_KEY }}'",
                "tests:",
                "  - vars:",
                "      accepted_plan: file://../sdlc/gate_inputs/final_plan.md",
                "      constraints: file://../sdlc/gate_inputs/final_constraints.json",
                "    assert:",
                "      - type: llm-rubric",
                "        value: ok",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    rendered = sdlc.render_eval_config_with_provider(config_path, sdlc.sdlc_provider_chain()[0])

    expected_plan = (tmp_path / "sdlc" / "gate_inputs" / "final_plan.md").resolve().as_posix()
    expected_constraints = (tmp_path / "sdlc" / "gate_inputs" / "final_constraints.json").resolve().as_posix()

    assert f"accepted_plan: file://{expected_plan}" in rendered
    assert f"constraints: file://{expected_constraints}" in rendered


def test_promptfoo_output_target_error_marks_gate_failed() -> None:
    sdlc = _load_sdlc_module()

    assert sdlc.promptfoo_output_has_target_error(
        "[ERROR] API error: 401 Unauthorized\nInvalid API Key\nEval aborted",
        "",
    )
    assert not sdlc.promptfoo_output_has_target_error("Results: 3 passed", "")
