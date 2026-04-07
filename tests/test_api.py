from mova_tool_sdk import Forge, Mova


def test_public_api_exposes_mova_execute_dry_run():
    client = Mova(dry_run=True, api_key="demo")
    result = client.execute(contract_id="finance.invoice_ocr_v1", input_data={"file_url": "https://example.com/a.png"})
    assert result["ok"] is True
    assert result["status"] == "dry-run"
    assert result["prepared_request"]["url"].endswith("/v1/bridge/contracts/finance.invoice_ocr_v1/runs")


def test_public_api_exposes_forge_stub():
    forge = Forge(api_key="demo")
    result = forge.start(intent="automate invoice processing")
    assert result["ok"] is True
    assert result["status"] == "scaffold"
