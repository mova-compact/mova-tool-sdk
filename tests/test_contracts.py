from pathlib import Path

from mova_tool_sdk.contracts import inspect_contract_package, validate_contract_package


def test_validate_contract_package_template():
    root = Path("D:/Projects_MOVA/mova-contract-spec/examples/invoice_processing_v0")
    result = validate_contract_package(root)
    assert result["ok"] is True


def test_inspect_contract_package_template():
    root = Path("D:/Projects_MOVA/mova-contract-spec/examples/invoice_processing_v0")
    result = inspect_contract_package(root)
    assert "contract_id" in result
