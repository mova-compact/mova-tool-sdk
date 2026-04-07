from mova_tool_sdk import Forge, Mova
from mova_tool_sdk.forge import ForgeSession


def test_public_api_exposes_mova_execute_dry_run():
    client = Mova(dry_run=True, api_key="demo")
    result = client.execute(
        contract_path="D:/Projects_MOVA/_mova_meta/templates/contract_package_v0",
        tenant_id="tenant_demo_shop_v0",
        input_data={"file_url": "https://example.com/a.png"},
    )
    assert result["ok"] is True
    assert result["status"] == "dry-run"
    assert result["prepared_request"]["url"].endswith("/intake/runs")


def test_public_api_exposes_forge_stub():
    forge = Forge(api_key="demo")
    session = forge.start(intent="automate invoice processing")
    assert isinstance(session, ForgeSession)
    assert session.contract_shape["contract_id"].startswith("contract.")
    assert session.current_step()["step_id"] == "problem_framing"
