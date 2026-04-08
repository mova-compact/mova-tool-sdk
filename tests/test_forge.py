import json
from pathlib import Path

from mova_tool_sdk.forge import ForgeSession, start_forge


def test_start_forge_builds_candidate_contract_shape():
    session = start_forge(intent="automate invoice processing with human approval")
    assert isinstance(session, ForgeSession)
    assert session.contract_shape["contract_id"].startswith("contract.")
    assert session.contract_shape["engine_execution_mode"] == "DRAFT_REVIEW"
    assert session.crystallized_intent["status"] == "candidate_ready"
    assert session.package_preview["manifest.json"]["schema_id"] == "package.contract_package_manifest_v0"
    assert session.package_preview["runtime_binding_set.json"]["bindings"][0]["execution_mode"] == "EXTERNAL_CALL"


def test_start_forge_shapes_finance_intent():
    session = start_forge(intent="automate invoice processing with IBAN check and human approval")
    assert session.contract_shape["contract_class"] == "finance"
    assert "file_url" in session.contract_shape["required_inputs"]
    assert session.contract_shape["binding_ref"] == "invoice_processing_v0"
    assert session.contract_shape["execution_mode"] == "EXTERNAL_CALL"


def test_candidate_summary_reports_handoff_ready_shape():
    session = start_forge(intent="triage support tickets")
    summary = session.candidate_summary()
    assert summary["contract_id"] == session.contract_shape["contract_id"]
    assert summary["contract_class"] == "ticket"
    assert summary["engine_execution_mode"] == "DRAFT_REVIEW"
    assert summary["unresolved_gaps"]


def test_forge_handoff_uses_platform_envelope():
    session = start_forge(intent="triage support tickets")
    handoff = session.to_local_candidate_handoff(target="authoring", tenant_ref="tenant_demo_shop_v0")
    assert handoff["env_type"] == "sdk_local_candidate_handoff_v2"
    assert handoff["handoff"]["target"] == "authoring"
    assert handoff["handoff"]["intent"] == "create_candidate_draft"
    assert handoff["actor_context"]["tenant_ref"] == "tenant_demo_shop_v0"
    assert handoff["candidate_package"]["canonical_package"]["manifest"]["package_id"] == session.contract_shape["contract_id"]


def test_forge_generate_package_writes_handoff_file():
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
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    binding_set = json.loads((output_dir / "runtime_binding_set.json").read_text(encoding="utf-8"))
    handoff = json.loads((output_dir / "sdk_local_candidate_handoff_v2.json").read_text(encoding="utf-8"))
    assert manifest["package_id"] == result["contract_id"]
    assert binding_set["bindings"][0]["notes"][1] == "derived_from_engine_mode:DRAFT_REVIEW"
    assert handoff["env_type"] == "sdk_local_candidate_handoff_v2"
    assert (output_dir / "models" / "input_model_v0.json").exists()
    assert (output_dir / "classification_results.json").exists()
    assert (output_dir / "flow.json").exists()
