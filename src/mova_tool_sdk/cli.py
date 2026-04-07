from __future__ import annotations

import argparse
import json
from pathlib import Path

from .client import MovaClient
from .config import MovaConfig, load_config, save_config
from .forge import start_forge
from .contracts import inspect_contract_package, validate_contract_package


def _client(config: MovaConfig, dry_run: bool) -> MovaClient:
    return MovaClient(
        api_key=config.api_key,
        base_url=config.base_url,
        dry_run=dry_run,
        admin_read_token=config.admin_read_token,
        runtime_execute_token=config.runtime_execute_token,
        operator_recovery_token=config.operator_recovery_token,
    )


def _print(payload: dict[str, object]) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("ok", True) else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mova")
    parser.add_argument("--dry-run", action="store_true")
    sub = parser.add_subparsers(dest="command")

    auth = sub.add_parser("auth")
    auth_sub = auth.add_subparsers(dest="auth_command")
    auth_set = auth_sub.add_parser("set-key")
    auth_set.add_argument("api_key")
    auth_scope = auth_sub.add_parser("set-scope-token")
    auth_scope.add_argument("scope", choices=["admin_read", "runtime_execute", "operator_recovery"])
    auth_scope.add_argument("token")
    auth_sub.add_parser("check")
    auth_sub.add_parser("whoami")

    forge = sub.add_parser("forge")
    forge.add_argument("--intent", required=True)
    forge.add_argument("--from")
    forge.add_argument("--output")

    validate = sub.add_parser("validate")
    validate.add_argument("path")

    inspect = sub.add_parser("inspect")
    inspect.add_argument("path")

    execute = sub.add_parser("execute")
    execute.add_argument("contract", nargs="?")
    execute.add_argument("--contract-id")
    execute.add_argument("--owner-id")
    execute.add_argument("--caller-id", default="caller.local")
    execute.add_argument("--tenant-id")
    execute.add_argument("--input")
    execute.add_argument("--input-file")

    status = sub.add_parser("status")
    status.add_argument("run_id")
    status.add_argument("--watch", action="store_true")

    decide = sub.add_parser("decide")
    decide.add_argument("run_id")
    decide.add_argument("option")
    decide.add_argument("--reason", required=True)

    audit = sub.add_parser("audit")
    audit.add_argument("run_id")
    audit.add_argument("--compact", action="store_true")
    audit.add_argument("--raw", action="store_true")
    audit.add_argument("--export")
    audit.add_argument("--verify", action="store_true")

    handoff = sub.add_parser("handoff")
    handoff.add_argument("--form-ref", required=True)
    handoff.add_argument("--intent")
    handoff.add_argument("--candidate-file")
    handoff.add_argument("--mode", choices=["guided", "direct"], default="guided")

    forms = sub.add_parser("forms")
    forms_sub = forms.add_subparsers(dest="forms_command")
    forms_sub.add_parser("list")
    form_get = forms_sub.add_parser("get")
    form_get.add_argument("form_id")

    draft = sub.add_parser("draft")
    draft.add_argument("session_id")

    authoring = sub.add_parser("authoring")
    authoring_sub = authoring.add_subparsers(dest="authoring_command")
    authoring_get = authoring_sub.add_parser("get")
    authoring_get.add_argument("session_id")
    authoring_answer = authoring_sub.add_parser("answer")
    authoring_answer.add_argument("session_id")
    authoring_answer.add_argument("field_id")
    authoring_answer.add_argument("--value", required=True)
    authoring_gap = authoring_sub.add_parser("gap-analysis")
    authoring_gap.add_argument("session_id")
    authoring_cancel = authoring_sub.add_parser("cancel")
    authoring_cancel.add_argument("session_id")

    lab = sub.add_parser("lab")
    lab.add_argument("--draft-ref", required=True)
    lab.add_argument("--fixture-set-ref", required=True)
    lab.add_argument("--mode", choices=["deterministic", "bounded_variance", "ai_assisted", "human_gated"], default="ai_assisted")
    lab.add_argument("--model-ref", default="sdk.local")

    lab_status = sub.add_parser("lab-status")
    lab_status.add_argument("lab_run_id")

    evidence = sub.add_parser("evidence")
    evidence_sub = evidence.add_subparsers(dest="evidence_command")
    evidence_sub.add_parser("list")
    evidence_get = evidence_sub.add_parser("get")
    evidence_get.add_argument("evidence_id")
    evidence_history = evidence_sub.add_parser("history")
    evidence_history.add_argument("evidence_id")
    evidence_lineage = evidence_sub.add_parser("lineage")
    evidence_lineage.add_argument("evidence_id")
    evidence_archive = evidence_sub.add_parser("archive")
    evidence_archive.add_argument("evidence_id")

    promote = sub.add_parser("promote")
    promote.add_argument("--draft-ref", required=True)
    promote.add_argument("--evidence-ref", required=True)
    promote.add_argument("--publisher-ref", required=True)
    promote.add_argument("--visibility", choices=["private", "public"], default="private")

    contracts = sub.add_parser("contracts")
    contracts_sub = contracts.add_subparsers(dest="contracts_command")
    contracts_sub.add_parser("list")
    contracts_get = contracts_sub.add_parser("get")
    contracts_get.add_argument("contract_id")
    contracts_history = contracts_sub.add_parser("history")
    contracts_history.add_argument("contract_id")
    contracts_lineage = contracts_sub.add_parser("lineage")
    contracts_lineage.add_argument("contract_id")
    contracts_publish = contracts_sub.add_parser("publish")
    contracts_publish.add_argument("contract_id")
    contracts_deprecate = contracts_sub.add_parser("deprecate")
    contracts_deprecate.add_argument("contract_id")
    contracts_retire = contracts_sub.add_parser("retire")
    contracts_retire.add_argument("contract_id")
    contracts_reactivate = contracts_sub.add_parser("reactivate")
    contracts_reactivate.add_argument("contract_id")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    config = load_config()

    if args.command == "auth":
        if args.auth_command == "set-key":
            config.api_key = args.api_key
            save_config(config)
            return _print({"ok": True, "status": "saved", "config_path": str(Path.home() / ".mova" / "config.json")})
        if args.auth_command == "set-scope-token":
            if args.scope == "admin_read":
                config.admin_read_token = args.token
            elif args.scope == "runtime_execute":
                config.runtime_execute_token = args.token
            elif args.scope == "operator_recovery":
                config.operator_recovery_token = args.token
            save_config(config)
            return _print({"ok": True, "status": "saved", "scope": args.scope})
        if args.auth_command == "check":
            return _print(
                {
                    "ok": bool(config.api_key or config.runtime_execute_token or config.admin_read_token),
                    "has_api_key": bool(config.api_key),
                    "has_admin_read_token": bool(config.admin_read_token),
                    "has_runtime_execute_token": bool(config.runtime_execute_token),
                    "has_operator_recovery_token": bool(config.operator_recovery_token),
                }
            )
        if args.auth_command == "whoami":
            return _print(
                {
                    "ok": True,
                    "profile_id": config.profile_id,
                    "default_owner_id": config.default_owner_id,
                    "base_url": config.base_url,
                    "has_api_key": bool(config.api_key),
                    "has_admin_read_token": bool(config.admin_read_token),
                    "has_runtime_execute_token": bool(config.runtime_execute_token),
                    "has_operator_recovery_token": bool(config.operator_recovery_token),
                }
            )

    if args.command == "forge":
        session = start_forge(intent=args.intent, source_path=args.__dict__.get("from"))
        result: dict[str, object] = {
            "ok": True,
            "status": "candidate_ready",
            "candidate": session.candidate_summary(),
            "handoff": session.to_local_candidate_handoff(),
            "next_step": "handoff_to_platform",
        }
        if args.output:
            generated = session.generate_package(args.output)
            result["package"] = generated
            result["next_step"] = "authoring_or_lab_in_state15"
        result["package_preview"] = session.package_preview
        return _print(result)

    if args.command == "validate":
        return _print(validate_contract_package(args.path))

    if args.command == "inspect":
        return _print({"ok": True, "contract": inspect_contract_package(args.path)})

    if args.command == "execute":
        contract_path = args.contract if args.contract and not args.contract_id else None
        input_payload: object | None = None
        if args.input:
            input_payload = json.loads(args.input)
        elif args.input_file:
            input_payload = json.loads(Path(args.input_file).read_text(encoding="utf-8"))
        payload = {
            "contract_path": contract_path,
            "contract_id": args.contract_id,
            "input_data": input_payload,
            "owner_id": args.owner_id or config.default_owner_id,
            "caller_id": args.caller_id,
            "tenant_id": args.tenant_id,
        }
        return _print(_client(config, args.dry_run).execute(**payload))

    if args.command == "handoff":
        if not args.intent and not args.candidate_file:
            return _print({"ok": False, "status": "missing_handoff_input"})
        client = _client(config, args.dry_run)
        if args.candidate_file:
            handoff_payload = json.loads(Path(args.candidate_file).read_text(encoding="utf-8"))
            return _print(
                client.create_authoring_session_from_handoff(
                    form_ref=args.form_ref,
                    handoff_payload=handoff_payload,
                    mode=args.mode,
                )
            )
        return _print(
            client.create_authoring_session(
                form_ref=args.form_ref,
                raw_minimum_intent=args.intent,
                mode=args.mode,
            )
        )

    if args.command == "forms":
        client = _client(config, args.dry_run)
        if args.forms_command == "list":
            return _print(client.list_authoring_forms())
        if args.forms_command == "get":
            return _print(client.get_authoring_form(args.form_id))
        return _print({"ok": False, "status": "missing_forms_command"})

    if args.command == "draft":
        return _print(_client(config, args.dry_run).emit_authoring_draft(args.session_id))

    if args.command == "authoring":
        client = _client(config, args.dry_run)
        if args.authoring_command == "get":
            return _print(client.get_authoring_session(args.session_id))
        if args.authoring_command == "answer":
            value: object
            raw = args.value
            try:
                value = json.loads(raw)
            except json.JSONDecodeError:
                value = raw
            return _print(client.answer_authoring_session(args.session_id, args.field_id, value))
        if args.authoring_command == "gap-analysis":
            return _print(client.gap_analysis_authoring_session(args.session_id))
        if args.authoring_command == "cancel":
            return _print(client.cancel_authoring_session(args.session_id))
        return _print({"ok": False, "status": "missing_authoring_command"})

    if args.command == "lab":
        return _print(
            _client(config, args.dry_run).create_lab_run(
                draft_contract_ref=args.draft_ref,
                fixture_set_ref=args.fixture_set_ref,
                execution_profile={
                    "mode": args.mode,
                    "model_ref": args.model_ref,
                },
            )
        )

    if args.command == "lab-status":
        return _print(_client(config, args.dry_run).get_lab_run(args.lab_run_id))

    if args.command == "evidence":
        client = _client(config, args.dry_run)
        if args.evidence_command == "list":
            return _print(client.list_lab_evidence())
        if args.evidence_command == "get":
            return _print(client.get_lab_evidence(args.evidence_id))
        if args.evidence_command == "history":
            return _print(client.get_lab_evidence_history(args.evidence_id))
        if args.evidence_command == "lineage":
            return _print(client.get_lab_evidence_lineage(args.evidence_id))
        if args.evidence_command == "archive":
            return _print(client.archive_lab_evidence(args.evidence_id))
        return _print({"ok": False, "status": "missing_evidence_command"})

    if args.command == "promote":
        return _print(
            _client(config, args.dry_run).promote_lab_draft(
                draft_contract_ref=args.draft_ref,
                evidence_ref=args.evidence_ref,
                publisher_ref=args.publisher_ref,
                visibility=args.visibility,
            )
        )

    if args.command == "contracts":
        client = _client(config, args.dry_run)
        if args.contracts_command == "list":
            return _print(client.list_contracts())
        if args.contracts_command == "get":
            return _print(client.pull_contract(args.contract_id))
        if args.contracts_command == "history":
            return _print(client.get_contract_history(args.contract_id))
        if args.contracts_command == "lineage":
            return _print(client.get_contract_lineage(args.contract_id))
        if args.contracts_command == "publish":
            return _print(client.publish_registered_contract(args.contract_id))
        if args.contracts_command == "deprecate":
            return _print(client.deprecate_contract(args.contract_id))
        if args.contracts_command == "retire":
            return _print(client.retire_contract(args.contract_id))
        if args.contracts_command == "reactivate":
            return _print(client.reactivate_contract(args.contract_id))
        return _print({"ok": False, "status": "missing_contracts_command"})

    if args.command == "status":
        result = _client(config, args.dry_run).get_run(args.run_id)
        if args.watch:
            result["watch"] = {"ok": True, "status": "scaffold", "message": "Watch mode is not wired yet."}
        return _print(result)

    if args.command == "decide":
        return _print(_client(config, args.dry_run).decide(args.run_id, args.option, args.reason))

    if args.command == "audit":
        result = _client(config, args.dry_run).audit(args.run_id)
        if args.verify:
            result["verification"] = {"ok": True, "status": "scaffold", "message": "Compact integrity verification is not wired yet."}
        if args.compact:
            result["view"] = "compact"
        elif args.raw:
            result["view"] = "raw"
        if args.export:
            Path(args.export).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            result["exported_to"] = str(Path(args.export).resolve())
        return _print(result)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
