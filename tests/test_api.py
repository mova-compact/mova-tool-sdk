from mova_tool_sdk import Forge, Mova
from mova_tool_sdk.forge import ForgeSession


def test_public_api_exposes_mova_execute_dry_run(example_contract_package):
    client = Mova(dry_run=True, api_key="demo")
    result = client.execute(
        contract_path=str(example_contract_package),
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


def test_public_api_exposes_identity_routes_dry_run():
    client = Mova(dry_run=True, api_key="demo")
    register = client.register("user@example.com")
    me = client.get_current_user()
    issue_key = client.create_api_key(["self_read", "runs_write"])
    assert register["prepared_request"]["headers"]["user-agent"].startswith("mova-tool-sdk/")
    assert register["prepared_request"]["headers"]["accept"] == "application/json"
    assert register["prepared_request"]["url"].endswith("/v1/register")
    assert register["prepared_request"]["payload"] == {"email": "user@example.com"}
    assert me["prepared_request"]["url"].endswith("/v1/me")
    assert issue_key["prepared_request"]["url"].endswith("/v1/api-keys")
    assert issue_key["prepared_request"]["payload"] == {"allowed_scopes": ["self_read", "runs_write"]}


def test_public_api_exposes_authoring_handoff_dry_run():
    client = Mova(dry_run=True, api_key="demo")
    result = client.create_authoring_session(
        form_ref="authoring_form_v0",
        raw_minimum_intent="triage support tickets",
    )
    assert result["ok"] is True
    assert result["status"] == "dry-run"
    assert result["prepared_request"]["url"].endswith("/v0/authoring/sessions")


def test_public_api_exposes_authoring_form_listing_dry_run():
    client = Mova(dry_run=True, api_key="demo")
    result = client.list_authoring_forms()
    assert result["ok"] is True
    assert result["status"] == "dry-run"
    assert result["prepared_request"]["url"].endswith("/v0/authoring/forms")


def test_public_api_exposes_authoring_answer_and_gap_analysis_dry_run():
    client = Mova(dry_run=True, api_key="demo")
    answer_result = client.answer_authoring_session("session_demo", "title", "Demo title")
    gap_result = client.gap_analysis_authoring_session("session_demo")
    cancel_result = client.cancel_authoring_session("session_demo")
    assert answer_result["prepared_request"]["url"].endswith("/v0/authoring/sessions/session_demo/answer")
    assert gap_result["prepared_request"]["url"].endswith("/v0/authoring/sessions/session_demo/gap-analysis")
    assert cancel_result["prepared_request"]["url"].endswith("/v0/authoring/sessions/session_demo/cancel")


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
    payload = result["prepared_request"]["payload"]
    assert payload["seed_source"] == "sdk_local_candidate_handoff_v2"
    assert payload["resolved_fields"]["contract_id"] == session.contract_shape["contract_id"]
    assert "seed_canonical_package" in payload


def test_public_api_accepts_v2_candidate_file_shape():
    client = Mova(dry_run=True, api_key="demo")
    result = client.create_authoring_session_from_handoff(
        form_ref="authoring_form_v0",
        handoff_payload={
            "env_type": "sdk_local_candidate_handoff_v2",
            "actor_context": {"tenant_ref": "tenant_demo_shop_v0"},
            "intent_context": {"raw_intent_text": "triage support tickets"},
            "handoff": {
                "target": "authoring",
                "intent": "create_candidate_draft",
                "raw_minimum_intent": "triage support tickets",
            },
            "candidate_package": {
                "canonical_package": {
                    "manifest": {
                        "schema_id": "package.contract_package_manifest_v0",
                        "package_id": "contract.demo.v0",
                        "package_version": "0.1.0",
                        "contract_id": "contract.demo.v0",
                        "start_step_id": "route_ticket",
                        "terminal_statuses": ["completed"],
                        "files": {},
                    }
                }
            },
        },
    )
    assert result["ok"] is True
    assert result["status"] == "dry-run"
    payload = result["prepared_request"]["payload"]
    assert payload["resolved_fields"]["contract_id"] == "contract.demo.v0"
    assert payload["seed_canonical_package"]["manifest"]["package_id"] == "contract.demo.v0"


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


def test_public_api_exposes_lab_evidence_routes_dry_run():
    client = Mova(dry_run=True, api_key="demo")
    listed = client.list_lab_evidence()
    item = client.get_lab_evidence("evidence_demo")
    history = client.get_lab_evidence_history("evidence_demo")
    lineage = client.get_lab_evidence_lineage("evidence_demo")
    archived = client.archive_lab_evidence("evidence_demo")
    assert listed["prepared_request"]["url"].endswith("/v0/lab/evidence")
    assert item["prepared_request"]["url"].endswith("/v0/lab/evidence/evidence_demo")
    assert history["prepared_request"]["url"].endswith("/v0/lab/evidence/evidence_demo/history")
    assert lineage["prepared_request"]["url"].endswith("/v0/lab/evidence/evidence_demo/lineage")
    assert archived["prepared_request"]["url"].endswith("/v0/lab/evidence/evidence_demo/archive")


def test_public_api_exposes_contract_registry_lifecycle_routes_dry_run():
    client = Mova(dry_run=True, api_key="demo")
    listed = client.list_contracts()
    item = client.pull_contract("pkg_demo_contract")
    history = client.get_contract_history("pkg_demo_contract")
    lineage = client.get_contract_lineage("pkg_demo_contract")
    published = client.publish_registered_contract("pkg_demo_contract")
    deprecated = client.deprecate_contract("pkg_demo_contract")
    retired = client.retire_contract("pkg_demo_contract")
    reactivated = client.reactivate_contract("pkg_demo_contract")
    assert listed["prepared_request"]["url"].endswith("/v0/registry/contracts")
    assert item["prepared_request"]["url"].endswith("/v0/registry/contracts/pkg_demo_contract")
    assert history["prepared_request"]["url"].endswith("/v0/registry/contracts/pkg_demo_contract/history")
    assert lineage["prepared_request"]["url"].endswith("/v0/registry/contracts/pkg_demo_contract/lineage")
    assert published["prepared_request"]["url"].endswith("/v0/registry/contracts/pkg_demo_contract/publish")
    assert deprecated["prepared_request"]["url"].endswith("/v0/registry/contracts/pkg_demo_contract/deprecate")
    assert retired["prepared_request"]["url"].endswith("/v0/registry/contracts/pkg_demo_contract/retire")
    assert reactivated["prepared_request"]["url"].endswith("/v0/registry/contracts/pkg_demo_contract/reactivate")


def test_public_api_exposes_business_connectors_routes_dry_run():
    client = Mova(dry_run=True, api_key="demo")
    listed = client.list_business_connectors()
    item = client.get_business_connector("connector.demo.v1")
    created = client.create_business_connector(
        connector_id="connector.demo.v1",
        title="Demo Connector",
        service_kind="mcp_proxy",
        auth_mode="bearer",
        supported_actions=["invoke"],
    )
    assert listed["prepared_request"]["url"].endswith("/v0/business/connectors")
    assert item["prepared_request"]["url"].endswith("/v0/business/connectors/connector.demo.v1")
    assert created["prepared_request"]["url"].endswith("/v0/business/connectors")


def test_public_api_exposes_business_bindings_routes_dry_run():
    client = Mova(dry_run=True, api_key="demo")
    listed = client.list_business_bindings()
    item = client.get_business_binding("binding.demo.v1")
    history = client.get_business_binding_history("binding.demo.v1")
    lineage = client.get_business_binding_lineage("binding.demo.v1")
    created = client.create_business_binding(
        binding_id="binding.demo.v1",
        organization_ref="org.demo",
        contract_ref="pkg_demo_contract",
        launch_profile_ref="profile.demo.v1",
        trigger={"kind": "manual"},
        resource_bindings=[],
        execution_mode="DRAFT_REVIEW",
        status="disabled",
    )
    attached = client.attach_business_binding("binding.demo.v1")
    rebound = client.rebind_business_binding("binding.demo.v1", status="disabled")
    activated = client.activate_business_binding("binding.demo.v1")
    enabled = client.enable_steady_state_business_binding("binding.demo.v1")
    paused = client.pause_business_binding("binding.demo.v1")
    disabled = client.disable_business_binding("binding.demo.v1")
    assert listed["prepared_request"]["url"].endswith("/v0/business/bindings")
    assert item["prepared_request"]["url"].endswith("/v0/business/bindings/binding.demo.v1")
    assert history["prepared_request"]["url"].endswith("/v0/business/bindings/binding.demo.v1/history")
    assert lineage["prepared_request"]["url"].endswith("/v0/business/bindings/binding.demo.v1/lineage")
    assert created["prepared_request"]["url"].endswith("/v0/business/bindings")
    assert attached["prepared_request"]["url"].endswith("/v0/business/bindings/binding.demo.v1/attach")
    assert rebound["prepared_request"]["url"].endswith("/v0/business/bindings/binding.demo.v1/rebind")
    assert activated["prepared_request"]["url"].endswith("/v0/business/bindings/binding.demo.v1/activate")
    assert enabled["prepared_request"]["url"].endswith("/v0/business/bindings/binding.demo.v1/enable-steady-state")
    assert paused["prepared_request"]["url"].endswith("/v0/business/bindings/binding.demo.v1/pause")
    assert disabled["prepared_request"]["url"].endswith("/v0/business/bindings/binding.demo.v1/disable")


def test_public_api_exposes_run_diagnostics_routes_dry_run():
    client = Mova(dry_run=True, api_key="demo")
    artifacts = client.get_run_artifacts("run_demo")
    admission = client.get_run_admission_result("run_demo")
    dispatch = client.get_run_dispatch_result("run_demo")
    execute_dry = client.get_run_execute_dry_result("run_demo")
    execute_internal = client.get_run_execute_internal_result("run_demo")
    continuation = client.get_run_continuation_result("run_demo")
    eligibility = client.get_run_runtime_eligibility("run_demo")
    access_grant = client.get_run_access_grant("run_demo")
    artifact = client.get_artifact("artifact_demo")
    assert artifacts["prepared_request"]["url"].endswith("/intake/runs/run_demo/artifacts")
    assert admission["prepared_request"]["url"].endswith("/intake/runs/run_demo/admission-result")
    assert dispatch["prepared_request"]["url"].endswith("/intake/runs/run_demo/dispatch-result")
    assert execute_dry["prepared_request"]["url"].endswith("/intake/runs/run_demo/execute-dry-result")
    assert execute_internal["prepared_request"]["url"].endswith("/intake/runs/run_demo/execute-internal-result")
    assert continuation["prepared_request"]["url"].endswith("/intake/runs/run_demo/continuation-result")
    assert eligibility["prepared_request"]["url"].endswith("/intake/runs/run_demo/runtime-eligibility")
    assert access_grant["prepared_request"]["url"].endswith("/intake/runs/run_demo/access-grant")
    assert artifact["prepared_request"]["url"].endswith("/artifacts/artifact_demo")


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
