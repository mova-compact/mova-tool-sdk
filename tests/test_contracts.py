from pathlib import Path

from mova_tool_sdk.contracts import inspect_contract_package, validate_contract_package


def test_validate_contract_package_template(example_contract_package):
    result = validate_contract_package(example_contract_package)
    assert result["ok"] is True


def test_inspect_contract_package_template(example_contract_package):
    result = inspect_contract_package(example_contract_package)
    assert "contract_id" in result
