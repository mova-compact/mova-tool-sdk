from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass

from .config import DEFAULT_BASE_URL
from .contracts import build_package_ref, load_package_projection


@dataclass
class MovaClient:
    api_key: str | None = None
    base_url: str = DEFAULT_BASE_URL
    dry_run: bool = False
    admin_read_token: str | None = None
    runtime_execute_token: str | None = None
    operator_recovery_token: str | None = None

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
        prepared = {
            "method": method,
            "url": f"{self.base_url.rstrip('/')}{path}",
            "payload": payload,
            "scope": scope,
        }
        if self.dry_run:
            return {"ok": True, "status": "dry-run", "prepared_request": prepared}

        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(prepared["url"], data=data, method=method)
        request.add_header("content-type", "application/json")
        token = self._token_for_scope(scope)
        if token:
            request.add_header("authorization", f"Bearer {token}")
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
        requested_status: str = "private_active",
    ) -> dict[str, object]:
        package_ref = build_package_ref(contract_path)
        package_projection = load_package_projection(contract_path)
        payload = {
            "owner_id": owner_id,
            "package_ref": package_ref,
            "requested_visibility": visibility,
            "requested_status": requested_status,
            "package_projection": package_projection,
        }
        return self._request("POST", "/v1/bridge/contracts/registrations", payload, scope="runtime_execute")

    def get_status(self, run_id: str) -> dict[str, object]:
        return self._request("GET", f"/v1/bridge/runs/{run_id}", scope="admin_read")

    def run_registered_contract(
        self,
        contract_id: str,
        input_data: object,
        caller_id: str,
        tenant_id: str | None = None,
        requested_surface: str = "mova_tool_sdk_v1",
    ) -> dict[str, object]:
        payload = {
            "contract_id": contract_id,
            "caller_id": caller_id,
            "input_ref": {
                "kind": "inline_json",
                "value": json.dumps(input_data),
            },
            "requested_surface": requested_surface,
        }
        if tenant_id:
            payload["tenant_id"] = tenant_id
        return self._request(
            "POST",
            f"/v1/bridge/contracts/{contract_id}/runs",
            payload,
            scope="runtime_execute",
        )

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
        resolved_contract_id = contract_id
        registration_result: dict[str, object] | None = None
        if contract_path:
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
            item = registration_result.get("item", {})
            if isinstance(item, dict):
                resolved_contract_id = item.get("contract_id") if isinstance(item.get("contract_id"), str) else resolved_contract_id

        if not resolved_contract_id:
            return {"ok": False, "status": "missing_contract_identity"}

        run_result = self.run_registered_contract(
            contract_id=resolved_contract_id,
            input_data=input_data,
            caller_id=caller_id,
            tenant_id=tenant_id,
        )
        if registration_result:
            run_result["registration"] = registration_result
        return run_result

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

    def register(self, email: str) -> dict[str, object]:
        return self._request("POST", "/v1/register", {"email": email})
