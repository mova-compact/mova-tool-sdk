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
    assert session.crystallized_intent["status"] == "candidate_ready"


def test_public_api_exposes_authoring_handoff_dry_run():
    client = Mova(dry_run=True, api_key="demo")
    result = client.create_authoring_session(
        form_ref="authoring_form_v0",
        raw_minimum_intent="triage support tickets",
    )
    assert result["ok"] is True
    assert result["status"] == "dry-run"
    assert result["prepared_request"]["url"].endswith("/v0/authoring/sessions")


def test_public_api_exposes_authoring_handoff_from_candidate_envelope():
    client = Mova(dry_run=True, api_key="demo")
    forge = Forge(api_key="demo")
    session = forge.start(intent="triage support tickets")
    result = client.create_authoring_session_from_handoff(
        form_ref="authoring_form_v0",
        handoff_payload=session.to_local_candidate_handoff(),
    )
    assert result["ok"] is True
    assert result["status"] == "dry-run"
    assert result["prepared_request"]["url"].endswith("/v0/authoring/sessions")


def test_public_api_exposes_lab_run_dry_run():
    client = Mova(dry_run=True, api_key="demo")
    result = client.create_lab_run(
        draft_contract_ref="artifact://draft.contract.v1",
        fixture_set_ref="fixture_set.ticket.v1",
        execution_profile={"mode": "ai_assisted", "model_ref": "sdk.local"},
    )
    assert result["ok"] is True
    assert result["status"] == "dry-run"
    assert result["prepared_request"]["url"].endswith("/v0/lab/runs")


def test_admin_read_dry_run_can_prepare_gateway_headers(monkeypatch):
    monkeypatch.setenv("MCP_DOOR_GATEWAY_KEY_ID", "gw_test")
    monkeypatch.setenv("MCP_DOOR_GATEWAY_SHARED_SECRET", "secret_test")
    monkeypatch.setenv("MCP_DOOR_ACTOR_ID", "principal.test")
    monkeypatch.setenv("MCP_DOOR_ACTOR_ROLE", "admin")
    monkeypatch.setenv("MCP_DOOR_ACTOR_TYPE", "human")
    client = Mova(dry_run=True, api_key="demo")
    result = client.list_authoring_forms()
    headers = result["prepared_request"]["headers"]
    assert result["ok"] is True
    assert headers["x-mova-gateway-key-id"] == "gw_test"
    assert headers["x-mova-actor-id"] == "principal.test"
    assert "x-mova-gateway-signature" in headers
