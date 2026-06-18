from synthetix.blueprints.models import SimulationBlueprint
from synthetix.execution.executor import response_schema
from synthetix.ingestion.questionnaire import QuestionnaireDraft
from synthetix.model_gateway.openrouter import strict_json_schema


def test_strict_json_schema_closes_every_object_node() -> None:
    schema = strict_json_schema(SimulationBlueprint.model_json_schema())

    def assert_strict(node: object) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object":
                assert node["additionalProperties"] is False
                assert set(node.get("required", [])) == set(node.get("properties", {}))
            for value in node.values():
                assert_strict(value)
        elif isinstance(node, list):
            for value in node:
                assert_strict(value)

    assert_strict(schema)


def test_questionnaire_draft_schema_uses_no_refs_or_unions() -> None:
    schema = strict_json_schema(QuestionnaireDraft.model_json_schema())
    rendered = str(schema)
    assert "$ref" not in rendered
    assert "anyOf" not in rendered


def test_survey_response_schema_has_fixed_array_shape() -> None:
    schema = strict_json_schema(response_schema())
    assert schema["required"] == ["responses"]
    item = schema["properties"]["responses"]["items"]
    assert item["required"] == ["question_id", "answer"]
    assert item["additionalProperties"] is False
