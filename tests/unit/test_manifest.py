from synthetix.blueprints.models import OpenTextQuestion, PopulationSpec, SimulationBlueprint
from synthetix.execution.manifest import RunManifest


def test_manifest_is_immutable_and_content_addressed() -> None:
    blueprint = SimulationBlueprint(
        title="Manifest",
        purpose="Record provenance.",
        population=PopulationSpec(size=1, seed=99),
        questions=[OpenTextQuestion(id="q1", prompt="Why?")],
    )
    manifest = RunManifest.create(
        run_id="run-1",
        blueprint=blueprint,
        source_hashes={"survey.yaml": "abc"},
        model_id="openai/gpt-4.1-mini",
        provider="openai",
        parameters={"temperature": 0.2},
    )
    assert manifest.blueprint_hash == blueprint.content_hash()
    assert len(manifest.manifest_hash()) == 64

