  gpt-5.4:
    role: "senior_planner_policy_reviewer_final_reviewer"
    purpose: "Own high-judgment work: product positioning, scientific boundary, benchmark/holdout governance, architecture decisions, final review, and SDLC gate decisions."
    allowed_paths:
    forbidden_paths:
    code_edit_rule: "Only for high-judgment policy, orchestration, benchmark governance, report semantics, or review fixes. Prefer delegating bounded plumbing to gpt-5.4-mini."
  gpt-5.4-mini:
    role: "bounded_implementer_test_writer_plumbing_agent"
    purpose: "Own scoped implementation, tests, fixtures, CLI plumbing, deterministic data contracts, and small refactors after GPT-5.4 has accepted the plan."
    allowed_paths:
    forbidden_paths:
    owner: "gpt-5.4"
    owner: "gpt-5.4"
    owner: "gpt-5.4"
    owner: "gpt-5.4"
    owner: "gpt-5.4"
    owner: "gpt-5.4"
    owner: "gpt-5.4"
    owner: "gpt-5.4"
    owner: "gpt-5.4-mini"
    reviewer: "gpt-5.4"
    owner: "gpt-5.4-mini"
    reviewer: "gpt-5.4"
    owner: "gpt-5.4-mini"
    reviewer: "gpt-5.4"
    owner: "gpt-5.4-mini"
    reviewer: "gpt-5.4"
    owner: "gpt-5.4-mini"
    reviewer: "gpt-5.4"
    owner: "gpt-5.4-mini"
    reviewer: "gpt-5.4"
    owner: "gpt-5.4"
    owner: "gpt-5.4-mini"
    owner: "gpt-5.4"
hard_rules:
