import json
from pathlib import Path

from mova_tool_sdk.forge import build_step_options, load_forge_session, normalize_choice, start_forge


def test_start_forge_builds_contract_shape():
    session = start_forge(intent="automate invoice processing with human approval")
    assert session.contract_shape["contract_id"].startswith("contract.")
    assert session.contract_shape["engine15_execution_mode"] == "DRAFT_REVIEW"
    assert session.crystallized_intent["status"] == "crystallization_complete"
    assert session.current_step()["step_id"] == "problem_framing"
    assert "result-definition" in session.current_step()["options"]
    assert session.is_complete() is False


def test_start_forge_shapes_finance_intent():
    session = start_forge(intent="automate invoice processing with IBAN check and human approval")
    assert session.contract_shape["contract_class"] == "finance"
    assert "file_url" in session.contract_shape["required_inputs"]
    assert "connector.document.ocr" in session.contract_shape["service_bindings"]
    assert "connector.human.review" in session.contract_shape["service_bindings"]
    assert session.contract_shape["source_execution_mode"] == "human_gated"
    assert session.contract_shape["terminal_outcomes"] == ["APPROVED", "REJECTED", "NEEDS_REVIEW"]


def test_forge_commit_advances_step():
    session = start_forge(intent="triage support tickets")
    result = session.commit("result-definition", "Need a bounded support triage contract")
    assert result["ok"] is True
    assert session.crystallized_intent["problem_framing"] == "result-definition"
    assert session.current_step()["step_id"] == "outcome"


def test_forge_outcome_choice_rebuilds_verification_model():
    session = start_forge(intent="triage support tickets")
    session.commit("result-definition", "Bound the task first")
    session.commit("decision_preparation", "Need a prepared decision packet")
    codes = session.package_preview["verification_model_v0.json"]["verification_codes"]
    assert codes[0]["code"] == "DECISION_READY"
    assert session.contract_shape["terminal_outcomes"][0] == "PREPARED"


def test_forge_strategy_choice_changes_execution_posture():
    session = start_forge(intent="triage support tickets")
    session.commit("result-definition", "Bound the task first")
    session.commit("artifact_creation", "Need a concrete output")
    session.commit("goal_plus_current_state", "Have current support state")
    session.commit("rigid_plan", "Prefer deterministic execution")
    assert session.contract_shape["source_execution_mode"] == "deterministic"
    assert session.package_preview["runtime_manifest_v0.json"]["execution_mode"] == "SAFE_INTERNAL"


def test_forge_decision_rights_choice_adds_human_gate():
    session = start_forge(intent="crm sync")
    session.commit("result-definition", "Bound the task first")
    session.commit("state_change", "Need a CRM update")
    session.commit("goal_plus_current_state", "Have current CRM state")
    session.commit("adaptive_feedback", "Need flexible handling")
    session.commit("combined_verification", "Need strong checks")
    session.commit("risk_tolerance", "Need review at risky points")
    session.commit("human_approves_final_only", "Human should approve the final change")
    assert "connector.human.review" in session.contract_shape["service_bindings"]
    assert session.package_preview["runtime_manifest_v0.json"]["capabilities"]["human_gated"] is True


def test_forge_commitment_updates_visibility():
    session = start_forge(intent="triage support tickets")
    while session.current_step()["step_id"] != "commitment":
        session.commit("default-choice", "Progress to commitment step")
    session.commit("publish_public_later", "I want to commercialize this contract later.")
    assert session.package_preview["source_contract_package_v0.json"]["visibility"] == "public"


def test_forge_session_save_and_load():
    session = start_forge(intent="triage support tickets")
    path = session.save(Path("tests") / "_forge_sessions")
    loaded = load_forge_session(session.session_id, Path("tests") / "_forge_sessions")
    assert path.exists()
    assert loaded.session_id == session.session_id
    assert loaded.current_step()["step_id"] == "problem_framing"
    path.unlink()
    path.parent.rmdir()


def test_forge_summary_reports_progress_and_snapshot():
    session = start_forge(intent="triage support tickets")
    session.commit("result-definition", "Need a bounded support triage contract")
    summary = session.summary()
    assert summary["progress"]["answered_steps"] == 1
    assert summary["progress"]["remaining_steps"] == len(session.steps) - 1
    assert summary["current_step"]["step_id"] == "outcome"
    assert summary["contract_snapshot"]["contract_id"] == session.contract_shape["contract_id"]
    assert summary["decisions"][0]["choice_label"] == "Result definition"
    assert summary["review"]["confirmed"] is False


def test_forge_summary_on_complete_session_has_no_current_step():
    session = start_forge(intent="triage support tickets")
    while not session.is_complete():
        step = session.current_step()
        session.commit(step["options"][0], "Progress to completion")
    summary = session.summary()
    assert summary["is_complete"] is True
    assert summary["current_step"] is None


def test_forge_back_rewinds_last_step_and_rebuilds_shape():
    session = start_forge(intent="triage support tickets")
    session.commit("result-definition", "Bound the task first")
    session.commit("decision_preparation", "Need a prepared decision packet")
    assert session.current_step()["step_id"] == "reality"
    result = session.back()
    assert result["ok"] is True
    assert session.current_step()["step_id"] == "outcome"
    assert session.answers == {"problem_framing": {"choice": "result-definition", "reason": "Bound the task first"}}
    assert session.crystallized_intent["outcome"] != "decision_preparation"
    codes = session.package_preview["verification_model_v0.json"]["verification_codes"]
    assert codes[0]["code"] != "DECISION_READY"


def test_forge_back_at_start_returns_error():
    session = start_forge(intent="triage support tickets")
    result = session.back()
    assert result["ok"] is False
    assert result["status"] == "at_start"


def test_forge_review_requires_completion_before_confirm():
    session = start_forge(intent="triage support tickets")
    result = session.review(confirm=True)
    assert result["ok"] is False
    assert result["status"] == "session_not_complete"


def test_forge_review_confirm_marks_session_ready_for_generation():
    session = start_forge(intent="triage support tickets")
    while not session.is_complete():
        step = session.current_step()
        session.commit(step["options"][0], "Progress to completion")
    result = session.review(confirm=True)
    assert result["ok"] is True
    assert result["status"] == "review_confirmed"
    assert session.review_confirmed is True
    assert result["summary"]["readiness"]["can_generate"] is True


def test_loaded_session_backfills_step_options():
    session = start_forge(intent="triage support tickets")
    path = session.save(Path("tests") / "_forge_sessions")
    payload = json.loads(path.read_text(encoding="utf-8"))
    for step in payload["steps"]:
        step.pop("options", None)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    loaded = load_forge_session(session.session_id, Path("tests") / "_forge_sessions")
    assert "artifact_creation" in loaded.steps[1]["options"]
    path.unlink()
    path.parent.rmdir()


def test_normalize_choice_accepts_alias_and_index():
    options = ["artifact_creation", "state_change", "behavior_change", "decision_preparation"]
    assert normalize_choice("outcome", "artifact", options) == "artifact_creation"
    assert normalize_choice("outcome", "4", options) == "decision_preparation"


def test_build_step_options_adds_labels_and_aliases():
    items = build_step_options("outcome", ["artifact_creation", "decision_preparation"])
    assert items[0]["index"] == 1
    assert items[0]["label"] == "Artifact creation"
    assert "artifact" in items[0]["aliases"]
    assert items[1]["label"] == "Decision preparation"


def test_start_forge_generates_package():
    output_dir = Path("tests") / "_forge_output"
    if output_dir.exists():
        for file_path in sorted(output_dir.rglob("*"), reverse=True):
            if file_path.is_file():
                file_path.unlink()
            elif file_path.is_dir():
                file_path.rmdir()
        output_dir.rmdir()
    session = start_forge(intent="automate invoice processing with human approval")
    result = session.generate_package(output_dir)
    assert result["ok"] is True
    source = json.loads((output_dir / "source_contract_package_v0.json").read_text(encoding="utf-8"))
    runtime = json.loads((output_dir / "runtime_manifest_v0.json").read_text(encoding="utf-8"))
    assert source["contract_id"] == result["contract_id"]
    assert runtime["execution_mode"] == "DRAFT_REVIEW"
    assert (output_dir / "validate_contract_package.py").exists()
