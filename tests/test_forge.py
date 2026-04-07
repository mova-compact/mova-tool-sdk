import json
from pathlib import Path

from mova_tool_sdk.forge import start_forge


def test_start_forge_builds_contract_shape():
    session = start_forge(intent="automate invoice processing with human approval")
    assert session.contract_shape["contract_id"].startswith("contract.")
    assert session.contract_shape["engine15_execution_mode"] == "DRAFT_REVIEW"
    assert session.crystallized_intent["status"] == "crystallization_complete"


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
