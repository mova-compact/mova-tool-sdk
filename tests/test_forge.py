import json
from pathlib import Path

from mova_tool_sdk.forge import load_forge_session, start_forge


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
