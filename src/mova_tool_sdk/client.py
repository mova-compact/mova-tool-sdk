from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse

from .config import DEFAULT_BASE_URL
from .contracts import load_package_projection, load_runtime_descriptor


def _as_record(value: object) -> dict[str, object] | None:
    return value if isinstance(value, dict) else None


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _handoff_seed_from_candidate(handoff_payload: dict[str, object]) -> dict[str, object] | None:
    candidate_package = _as_record(handoff_payload.get("candidate_package"))
    canonical_package = _as_record(candidate_package.get("canonical_package")) if candidate_package else None
    if not canonical_package:
        return None

    manifest = _as_record(canonical_package.get("manifest")) or {}
    flow = _as_record(canonical_package.get("flow")) or {}
    classification_policy = _as_record(canonical_package.get("classification_policy")) or {}
    runtime_binding_set = _as_record(canonical_package.get("runtime_binding_set")) or {}
    intent_context = _as_record(handoff_payload.get("intent_context")) or {}

    contract_id = str(manifest.get("package_id") or flow.get("flow_id") or "draft.contract")
    raw_intent = str(intent_context.get("raw_intent_text") or "").strip()
    summary = str(intent_context.get("goal_description") or flow.get("flow_intent") or raw_intent or contract_id)

    bindings = [item for item in _as_list(runtime_binding_set.get("bindings")) if isinstance(item, dict)]
    external_binding_refs = [
        str(item.get("binding_ref"))
        for item in bindings
        if str(item.get("binding_kind") or "") == "mcp_tool_call" and str(item.get("binding_ref") or "").strip()
    ]
    execution_mode = next(
        (
            str(item.get("execution_mode"))
            for item in bindings
            if str(item.get("execution_mode") or "").strip()
        ),
        "DETERMINISTIC",
    )

    return {
        "contract_id": contract_id,
        "title": contract_id,
        "summary": summary,
        "intent_ref": f"intent://sdk-local/{contract_id}",
        "policy_ref": str(classification_policy.get("policy_id") or "mova.step_classification_policy_v0"),
        "transition_rule_ref": f"transition://{contract_id}/default",
        "service_bindings": external_binding_refs,
        "required_connections": external_binding_refs,
        "execution_mode": execution_mode,
    }


@dataclass
class MovaClient:
    api_key: str | None = None
    base_url: str = DEFAULT_BASE_URL
    dry_run: bool = False
    admin_read_token: str | None = None
    runtime_execute_token: str | None = None
    operator_recovery_token: str | None = None

    def _gateway_credentials(self, scope: str) -> dict[str, str] | None:
        if scope != "admin_read":
            return None
        key_id = os.environ.get("MCP_DOOR_GATEWAY_KEY_ID")
        shared_secret = os.environ.get("MCP_DOOR_GATEWAY_SHARED_SECRET")
        actor_id = os.environ.get("MCP_DOOR_ACTOR_ID")
        actor_role = os.environ.get("MCP_DOOR_ACTOR_ROLE")
        actor_type = os.environ.get("MCP_DOOR_ACTOR_TYPE") or "human"
        if not key_id or not shared_secret or not actor_id or not actor_role:
            return None
        return {
            "key_id": key_id,
            "shared_secret": shared_secret,
            "actor_id": actor_id,
            "actor_role": actor_role,
            "actor_type": actor_type,
        }

    def _build_gateway_headers(self, url: str, method: str, scope: str) -> dict[str, str]:
        creds = self._gateway_credentials(scope)
        if not creds:
            return {}
        timestamp = str(int(time.time()))
        path = urlparse(url).path or "/"
        payload = "\n".join(
            [
                "mova-admin-gateway-v1",
                timestamp,
                method.upper(),
                path,
                scope,
                creds["actor_id"],
                creds["actor_role"],
                creds["actor_type"],
            ]
        )
        signature = hmac.new(
            creds["shared_secret"].encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        return {
            "x-mova-gateway-key-id": creds["key_id"],
            "x-mova-gateway-timestamp": timestamp,
            "x-mova-gateway-signature": signature,
            "x-mova-actor-id": creds["actor_id"],
            "x-mova-actor-role": creds["actor_role"],
            "x-mova-actor-type": creds["actor_type"],
        }

    def _token_for_scope(self, scope: str) -> str | None:
        if scope == "admin_read":
            return self.admin_read_token or os.environ.get("MOVA_ADMIN_READ_TOKEN") or self.api_key
        if scope == "runtime_execute":
            return self.runtime_execute_token or os.environ.get("MOVA_RUNTIME_EXECUTE_TOKEN") or self.api_key
        if scope == "operator_recovery":
            return self.operator_recovery_token or os.environ.get("MOVA_OPERATOR_RECOVERY_TOKEN") or self.api_key
        return self.api_key

    def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, object] | None = None,
        scope: str = "runtime_execute",
    ) -> dict[str, object]:
        url = f"{self.base_url.rstrip('/')}{path}"
        headers = {"content-type": "application/json"}
        prepared = {
            "method": method,
            "url": url,
            "payload": payload,
            "scope": scope,
            "headers": headers,
        }
        headers.update(self._build_gateway_headers(url, method, scope))
        if self.dry_run:
            prepared["headers"] = headers
            return {"ok": True, "status": "dry-run", "prepared_request": prepared}

        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(prepared["url"], data=data, method=method)
        token = self._token_for_scope(scope)
        if token:
            headers["authorization"] = f"Bearer {token}"
        prepared["headers"] = headers
        for header_name, header_value in headers.items():
            request.add_header(header_name, header_value)
        try:
            with urllib.request.urlopen(request) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {"ok": True}
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8")
            try:
                parsed = json.loads(body) if body else {}
            except json.JSONDecodeError:
                parsed = {"raw": body}
            return {
                "ok": False,
                "status": f"http_{exc.code}",
                "error": parsed,
                "prepared_request": prepared,
            }

    def register_contract_package(
        self,
        contract_path: str,
        owner_id: str,
        visibility: str = "private",
        requested_status: str = "validated",
    ) -> dict[str, object]:
        payload = load_package_projection(contract_path)
        payload["publisher_ref"] = owner_id
        payload["visibility"] = visibility
        payload["status"] = requested_status
        return self._request("POST", "/v0/registry/contracts", payload, scope="runtime_execute")

    def publish_contract(
        self,
        contract_path: str,
        owner_id: str,
        *,
        public: bool = False,
    ) -> dict[str, object]:
        visibility = "public" if public else "private"
        requested_status = "public_active" if public else "private_active"
        return self.register_contract_package(
            contract_path=contract_path,
            owner_id=owner_id,
            visibility=visibility,
            requested_status=requested_status,
        )

    def list_contracts(self) -> dict[str, object]:
        return self._request("GET", "/v0/registry/contracts", scope="admin_read")

    def pull_contract(self, contract_id: str) -> dict[str, object]:
        return self._request("GET", f"/v0/registry/contracts/{contract_id}", scope="admin_read")

    def get_contract_history(self, contract_id: str) -> dict[str, object]:
        return self._request("GET", f"/v0/registry/contracts/{contract_id}/history", scope="admin_read")

    def get_contract_lineage(self, contract_id: str) -> dict[str, object]:
        return self._request("GET", f"/v0/registry/contracts/{contract_id}/lineage", scope="admin_read")

    def publish_registered_contract(self, contract_id: str) -> dict[str, object]:
        return self._request("POST", f"/v0/registry/contracts/{contract_id}/publish", {}, scope="runtime_execute")

    def deprecate_contract(self, contract_id: str) -> dict[str, object]:
        return self._request("POST", f"/v0/registry/contracts/{contract_id}/deprecate", {}, scope="runtime_execute")

    def retire_contract(self, contract_id: str) -> dict[str, object]:
        return self._request("POST", f"/v0/registry/contracts/{contract_id}/retire", {}, scope="runtime_execute")

    def reactivate_contract(self, contract_id: str) -> dict[str, object]:
        return self._request("POST", f"/v0/registry/contracts/{contract_id}/reactivate", {}, scope="runtime_execute")

    def list_business_connectors(self) -> dict[str, object]:
        return self._request("GET", "/v0/business/connectors", scope="admin_read")

    def get_business_connector(self, connector_id: str) -> dict[str, object]:
        return self._request("GET", f"/v0/business/connectors/{connector_id}", scope="admin_read")

    def create_business_connector(
        self,
        *,
        connector_id: str,
        title: str,
        service_kind: str,
        auth_mode: str,
        supported_actions: list[str],
        status: str = "active",
        version: str = "1.0.0",
        input_schema_ref: str | None = None,
        output_schema_ref: str | None = None,
        rate_limit_profile: dict[str, object] | None = None,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "connector_id": connector_id,
            "title": title,
            "service_kind": service_kind,
            "auth_mode": auth_mode,
            "supported_actions": supported_actions,
            "status": status,
            "version": version,
        }
        if input_schema_ref:
            payload["input_schema_ref"] = input_schema_ref
        if output_schema_ref:
            payload["output_schema_ref"] = output_schema_ref
        if rate_limit_profile is not None:
            payload["rate_limit_profile"] = rate_limit_profile
        return self._request("POST", "/v0/business/connectors", payload, scope="runtime_execute")

    def list_business_bindings(self) -> dict[str, object]:
        return self._request("GET", "/v0/business/bindings", scope="admin_read")

    def get_business_binding(self, binding_id: str) -> dict[str, object]:
        return self._request("GET", f"/v0/business/bindings/{binding_id}", scope="admin_read")

    def get_business_binding_history(self, binding_id: str) -> dict[str, object]:
        return self._request("GET", f"/v0/business/bindings/{binding_id}/history", scope="admin_read")

    def get_business_binding_lineage(self, binding_id: str) -> dict[str, object]:
        return self._request("GET", f"/v0/business/bindings/{binding_id}/lineage", scope="admin_read")

    def create_business_binding(
        self,
        *,
        binding_id: str,
        organization_ref: str,
        contract_ref: str,
        launch_profile_ref: str,
        trigger: dict[str, object],
        resource_bindings: list[object],
        execution_mode: str,
        status: str,
        input_defaults: dict[str, object] | None = None,
        policy_override_ref: str | None = None,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "binding_id": binding_id,
            "organization_ref": organization_ref,
            "contract_ref": contract_ref,
            "launch_profile_ref": launch_profile_ref,
            "trigger": trigger,
            "resource_bindings": resource_bindings,
            "execution_mode": execution_mode,
            "status": status,
        }
        if input_defaults is not None:
            payload["input_defaults"] = input_defaults
        if policy_override_ref:
            payload["policy_override_ref"] = policy_override_ref
        return self._request("POST", "/v0/business/bindings", payload, scope="runtime_execute")

    def attach_business_binding(self, binding_id: str, new_binding_id: str | None = None) -> dict[str, object]:
        payload = {"new_binding_id": new_binding_id} if new_binding_id else {}
        return self._request("POST", f"/v0/business/bindings/{binding_id}/attach", payload, scope="runtime_execute")

    def rebind_business_binding(
        self,
        binding_id: str,
        *,
        new_binding_id: str | None = None,
        organization_ref: str | None = None,
        contract_ref: str | None = None,
        launch_profile_ref: str | None = None,
        trigger: dict[str, object] | None = None,
        resource_bindings: list[object] | None = None,
        input_defaults: dict[str, object] | None = None,
        execution_mode: str | None = None,
        policy_override_ref: str | None = None,
        status: str | None = None,
    ) -> dict[str, object]:
        payload: dict[str, object] = {}
        if new_binding_id:
            payload["new_binding_id"] = new_binding_id
        if organization_ref:
            payload["organization_ref"] = organization_ref
        if contract_ref:
            payload["contract_ref"] = contract_ref
        if launch_profile_ref:
            payload["launch_profile_ref"] = launch_profile_ref
        if trigger is not None:
            payload["trigger"] = trigger
        if resource_bindings is not None:
            payload["resource_bindings"] = resource_bindings
        if input_defaults is not None:
            payload["input_defaults"] = input_defaults
        if execution_mode:
            payload["execution_mode"] = execution_mode
        if policy_override_ref:
            payload["policy_override_ref"] = policy_override_ref
        if status:
            payload["status"] = status
        return self._request("POST", f"/v0/business/bindings/{binding_id}/rebind", payload, scope="runtime_execute")

    def activate_business_binding(self, binding_id: str) -> dict[str, object]:
        return self._request("POST", f"/v0/business/bindings/{binding_id}/activate", {}, scope="runtime_execute")

    def enable_steady_state_business_binding(self, binding_id: str) -> dict[str, object]:
        return self._request("POST", f"/v0/business/bindings/{binding_id}/enable-steady-state", {}, scope="runtime_execute")

    def pause_business_binding(self, binding_id: str) -> dict[str, object]:
        return self._request("POST", f"/v0/business/bindings/{binding_id}/pause", {}, scope="runtime_execute")

    def disable_business_binding(self, binding_id: str) -> dict[str, object]:
        return self._request("POST", f"/v0/business/bindings/{binding_id}/disable", {}, scope="runtime_execute")

    def get_status(self, run_id: str) -> dict[str, object]:
        return self._request("GET", f"/intake/runs/{run_id}", scope="admin_read")

    def get_run(self, run_id: str) -> dict[str, object]:
        return self.get_status(run_id)

    def list_authoring_forms(self) -> dict[str, object]:
        return self._request("GET", "/v0/authoring/forms", scope="admin_read")

    def get_authoring_form(self, form_id: str) -> dict[str, object]:
        return self._request("GET", f"/v0/authoring/forms/{form_id}", scope="admin_read")

    def create_authoring_session(
        self,
        *,
        form_ref: str,
        raw_minimum_intent: str,
        mode: str = "guided",
        resolved_fields: dict[str, object] | None = None,
        seed_canonical_package: dict[str, object] | None = None,
        seed_source: str | None = None,
    ) -> dict[str, object]:
        payload = {
            "mode": mode,
            "form_ref": form_ref,
            "raw_minimum_intent": raw_minimum_intent,
        }
        if resolved_fields:
            payload["resolved_fields"] = resolved_fields
        if seed_canonical_package:
            payload["seed_canonical_package"] = seed_canonical_package
        if seed_source:
            payload["seed_source"] = seed_source
        return self._request("POST", "/v0/authoring/sessions", payload, scope="runtime_execute")

    def create_authoring_session_from_handoff(
        self,
        *,
        form_ref: str,
        handoff_payload: dict[str, object],
        mode: str = "guided",
    ) -> dict[str, object]:
        if handoff_payload.get("env_type") not in {"sdk_local_candidate_handoff_v1", "sdk_local_candidate_handoff_v2"}:
            return {"ok": False, "status": "invalid_handoff_env_type"}
        intent_context = handoff_payload.get("intent_context", {})
        raw_minimum_intent = ""
        if isinstance(intent_context, dict):
            raw_value = intent_context.get("raw_intent_text")
            if isinstance(raw_value, str):
                raw_minimum_intent = raw_value
        if not raw_minimum_intent:
            handoff = handoff_payload.get("handoff", {})
            if isinstance(handoff, dict):
                raw_value = handoff.get("raw_minimum_intent")
                if isinstance(raw_value, str):
                    raw_minimum_intent = raw_value
        if not raw_minimum_intent:
            return {"ok": False, "status": "missing_raw_intent_text"}
        seed_fields = _handoff_seed_from_candidate(handoff_payload)
        candidate_package = _as_record(handoff_payload.get("candidate_package")) or {}
        canonical_package = _as_record(candidate_package.get("canonical_package"))
        return self.create_authoring_session(
            form_ref=form_ref,
            raw_minimum_intent=raw_minimum_intent,
            mode=mode,
            resolved_fields=seed_fields,
            seed_canonical_package=canonical_package,
            seed_source=str(handoff_payload.get("env_type") or "sdk_local_candidate_handoff"),
        )

    def get_authoring_session(self, session_id: str) -> dict[str, object]:
        return self._request("GET", f"/v0/authoring/sessions/{session_id}", scope="admin_read")

    def answer_authoring_session(self, session_id: str, field_id: str, value: object) -> dict[str, object]:
        payload = {"field_id": field_id, "value": value}
        return self._request(
            "POST",
            f"/v0/authoring/sessions/{session_id}/answer",
            payload,
            scope="runtime_execute",
        )

    def gap_analysis_authoring_session(self, session_id: str) -> dict[str, object]:
        return self._request(
            "POST",
            f"/v0/authoring/sessions/{session_id}/gap-analysis",
            {},
            scope="runtime_execute",
        )

    def emit_authoring_draft(self, session_id: str) -> dict[str, object]:
        return self._request(
            "POST",
            f"/v0/authoring/sessions/{session_id}/emit-draft",
            {},
            scope="runtime_execute",
        )

    def cancel_authoring_session(self, session_id: str) -> dict[str, object]:
        return self._request(
            "POST",
            f"/v0/authoring/sessions/{session_id}/cancel",
            {},
            scope="runtime_execute",
        )

    def create_lab_run(
        self,
        *,
        draft_contract_ref: str,
        fixture_set_ref: str,
        execution_profile: dict[str, object],
    ) -> dict[str, object]:
        payload = {
            "draft_contract_ref": draft_contract_ref,
            "fixture_set_ref": fixture_set_ref,
            "execution_profile": execution_profile,
        }
        return self._request("POST", "/v0/lab/runs", payload, scope="runtime_execute")

    def get_lab_run(self, lab_run_id: str) -> dict[str, object]:
        return self._request("GET", f"/v0/lab/runs/{lab_run_id}", scope="admin_read")

    def list_lab_evidence(self) -> dict[str, object]:
        return self._request("GET", "/v0/lab/evidence", scope="admin_read")

    def get_lab_evidence(self, evidence_id: str) -> dict[str, object]:
        return self._request("GET", f"/v0/lab/evidence/{evidence_id}", scope="admin_read")

    def get_lab_evidence_history(self, evidence_id: str) -> dict[str, object]:
        return self._request("GET", f"/v0/lab/evidence/{evidence_id}/history", scope="admin_read")

    def get_lab_evidence_lineage(self, evidence_id: str) -> dict[str, object]:
        return self._request("GET", f"/v0/lab/evidence/{evidence_id}/lineage", scope="admin_read")

    def archive_lab_evidence(self, evidence_id: str) -> dict[str, object]:
        return self._request(
            "POST",
            f"/v0/lab/evidence/{evidence_id}/archive",
            {},
            scope="runtime_execute",
        )

    def promote_lab_draft(
        self,
        *,
        draft_contract_ref: str,
        evidence_ref: str,
        publisher_ref: str,
        visibility: str,
    ) -> dict[str, object]:
        payload = {
            "draft_contract_ref": draft_contract_ref,
            "evidence_ref": evidence_ref,
            "publisher_ref": publisher_ref,
            "visibility": visibility,
        }
        return self._request("POST", "/v0/lab/promote", payload, scope="runtime_execute")

    def list_runs(self) -> dict[str, object]:
        return {
            "ok": True,
            "status": "scaffold",
            "message": "Run listing will move to an SDK-native platform endpoint.",
        }

    def create_run(
        self,
        *,
        tenant_id: str,
        process_contract_ref: str,
        input_data: object,
        requested_surface: str = "mova_tool_sdk",
        execution_mode: str | None = None,
    ) -> dict[str, object]:
        payload = {
            "tenant_id": tenant_id,
            "process_contract_ref": process_contract_ref,
            "requested_surface": requested_surface,
            "intake_payload": input_data if isinstance(input_data, dict) else {"input": input_data},
        }
        if execution_mode:
            payload["execution_mode"] = execution_mode
        return self._request("POST", "/intake/runs", payload, scope="runtime_execute")

    def execute_contract(
        self,
        *,
        contract_path: str | None = None,
        contract_id: str | None = None,
        input_data: object | None = None,
        owner_id: str | None = None,
        caller_id: str = "caller.local",
        tenant_id: str | None = None,
    ) -> dict[str, object]:
        resolved_process_contract_ref: str | None = None
        resolved_execution_mode: str | None = None
        registration_result: dict[str, object] | None = None
        if contract_path:
            runtime_manifest = load_runtime_descriptor(contract_path)
            registration_result = self.register_contract_package(
                contract_path=contract_path,
                owner_id=owner_id or "owner.local",
            )
            if not registration_result.get("ok"):
                return {
                    "ok": False,
                    "status": "registration_failed",
                    "registration": registration_result,
                }
            resolved_process_contract_ref = (
                runtime_manifest.get("process_contract_ref")
                if isinstance(runtime_manifest.get("process_contract_ref"), str)
                else None
            )
            resolved_execution_mode = (
                runtime_manifest.get("engine_execution_mode")
                if isinstance(runtime_manifest.get("engine_execution_mode"), str)
                else None
            )

        if contract_id and not contract_path:
            return {
                "ok": False,
                "status": "contract_id_execution_not_supported_yet",
                "contract_id": contract_id,
                "hint": "Use a local contract package path until the platform exposes contract_id to runtime resolution.",
            }

        if not tenant_id:
            return {"ok": False, "status": "missing_tenant_id"}

        if not resolved_process_contract_ref:
            return {"ok": False, "status": "missing_process_contract_ref"}

        run_result = self.create_run(
            tenant_id=tenant_id,
            process_contract_ref=resolved_process_contract_ref,
            input_data=input_data,
            requested_surface="mova_tool_sdk",
            execution_mode=resolved_execution_mode,
        )
        if registration_result:
            run_result["registration"] = registration_result
        if caller_id:
            run_result["caller_id"] = caller_id
        return run_result

    def execute(
        self,
        *,
        contract_path: str | None = None,
        contract_id: str | None = None,
        input_data: object | None = None,
        owner_id: str | None = None,
        caller_id: str = "caller.local",
        tenant_id: str | None = None,
    ) -> dict[str, object]:
        return self.execute_contract(
            contract_path=contract_path,
            contract_id=contract_id,
            input_data=input_data,
            owner_id=owner_id,
            caller_id=caller_id,
            tenant_id=tenant_id,
        )

    def decide(self, run_id: str, option: str, reason: str) -> dict[str, object]:
        normalized = option.strip().lower()
        if normalized not in {"approve", "approved", "deny", "denied", "reject"}:
            return {
                "ok": False,
                "status": "unsupported_decision_option",
                "supported": ["approve", "deny"],
            }
        decision_path = "approve" if normalized in {"approve", "approved"} else "deny"
        payload = {
            "operator_ref": "operator://mova-tool-sdk",
            "note": reason,
            "continue_execution": decision_path == "approve",
        }
        return self._request(
            "POST",
            f"/operator/runs/{run_id}/{decision_path}",
            payload,
            scope="operator_recovery",
        )

    def get_audit(self, run_id: str) -> dict[str, object]:
        return self._request("GET", f"/v0/admin/audit/runs/{run_id}/export", scope="admin_read")

    def audit(self, run_id: str) -> dict[str, object]:
        return self.get_audit(run_id)

    def pending_decisions(self) -> dict[str, object]:
        return {
            "ok": True,
            "status": "scaffold",
            "message": "Pending decision listing is not wired yet.",
        }

    def register(self, email: str) -> dict[str, object]:
        return self._request("POST", "/v1/register", {"email": email})
