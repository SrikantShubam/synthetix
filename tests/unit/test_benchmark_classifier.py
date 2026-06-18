from __future__ import annotations

from synthetix.benchmarking.classifier import BenchmarkClassifier, BenchmarkFamily


def test_classifier_identifies_privacy_decision_surveys() -> None:
    classification = BenchmarkClassifier.classify(
        title="Privacy preference survey",
        purpose="Explore online privacy and security choices",
        questions=[
            "Would you share location data with this app?",
            "How concerned are you about personal data collection?",
        ],
    )

    assert classification.family == BenchmarkFamily.PRIVACY_DECISIONS
    assert classification.status == "benchmarkable"
    assert classification.threshold_label == "privacy-decision benchmark"


def test_classifier_marks_unsupported_domain_not_benchmarkable() -> None:
    classification = BenchmarkClassifier.classify(
        title="Dog behavior survey",
        purpose="Understand how dogs react to toys and food bowls",
        questions=[
            "Does the dog prefer rope toys?",
            "How often does the dog bark at delivery drivers?",
        ],
    )

    assert classification.family == BenchmarkFamily.UNSUPPORTED
    assert classification.status == "not_benchmarkable"
    assert classification.threshold_label is None


def test_classifier_identifies_subgroup_comparison_surveys() -> None:
    classification = BenchmarkClassifier.classify(
        title="Workplace climate survey",
        purpose="Compare inclusion and satisfaction across gender and region",
        questions=[
            "How satisfied are you with the climate?",
            "Have you experienced discrimination?",
        ],
    )

    assert classification.family == BenchmarkFamily.SUBGROUP_COMPARISON
    assert classification.status == "benchmarkable"
