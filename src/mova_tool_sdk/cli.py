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

    register = sub.add_parser("register")
    register.add_argument("--email", required=True)

    publish = sub.add_parser("publish")
    visibility = publish.add_mutually_exclusive_group(required=True)
    visibility.add_argument("--private", action="store_true")
    visibility.add_argument("--public", action="store_true")
    publish.add_argument("path")
    publish.add_argument("--owner-id")

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
    forge.add_argument("--intent")
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

    decisions = sub.add_parser("decisions")
    decisions_sub = decisions.add_subparsers(dest="decisions_command")
    decisions_sub.add_parser("pending")

    audit = sub.add_parser("audit")
    audit.add_argument("run_id")
    audit.add_argument("--compact", action="store_true")
    audit.add_argument("--raw", action="store_true")
    audit.add_argument("--export")
    audit.add_argument("--verify", action="store_true")

    connectors = sub.add_parser("connectors")
    connectors_sub = connectors.add_subparsers(dest="connectors_command")
    connectors_sub.add_parser("list")
    connectors_sub.add_parser("registered")
    connectors_test = connectors_sub.add_parser("test")
    connectors_test.add_argument("connector_id")
    connectors_add = connectors_sub.add_parser("add")
    connectors_add.add_argument("--id", required=True)
    connectors_add.add_argument("--url", required=True)
    connectors_add.add_argument("--auth", required=True)
    connectors_add.add_argument("--token")
    connectors_remove = connectors_sub.add_parser("remove")
    connectors_remove.add_argument("connector_id")

    contracts = sub.add_parser("contracts")
    contracts_sub = contracts.add_subparsers(dest="contracts_command")
    contracts_sub.add_parser("list")
    contracts_pull = contracts_sub.add_parser("pull")
    contracts_pull.add_argument("contract_id")

    usage = sub.add_parser("usage")
    usage.add_argument("--from")
    usage.add_argument("--to")

    sub.add_parser("plan")

    cost = sub.add_parser("cost")
    cost.add_argument("run_id")

    runs = sub.add_parser("runs")
    runs_sub = runs.add_subparsers(dest="runs_command")
    runs_sub.add_parser("list")

    serve = sub.add_parser("serve")
    serve.add_argument("--mode", required=True)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    config = load_config()

    if args.command == "register":
        result = _client(config, args.dry_run).register(args.email)
        return _print(result)

    if args.command == "publish":
        owner_id = args.owner_id or config.default_owner_id
        if not owner_id:
            return _print({"ok": False, "status": "missing_owner_id"})
        result = _client(config, args.dry_run).publish_contract(
            contract_path=args.path,
            owner_id=owner_id,
            public=bool(args.public),
        )
        return _print(result)

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
            "status": "started",
            "current_step": session.current_step(),
            "is_complete": session.is_complete(),
            "crystallized_intent": session.crystallized_intent,
            "contract_shape": session.contract_shape,
            "next_step": "review_contract_shape",
        }
        if args.output:
            generated = session.generate_package(args.output)
            result["package"] = generated
            result["next_step"] = "review_generated_package"
        else:
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

    if args.command == "status":
        result = _client(config, args.dry_run).get_run(args.run_id)
        if args.watch:
            result["watch"] = {"ok": True, "status": "scaffold", "message": "Watch mode is not wired yet."}
        return _print(result)

    if args.command == "decide":
        return _print(_client(config, args.dry_run).decide(args.run_id, args.option, args.reason))

    if args.command == "decisions":
        if args.decisions_command == "pending":
            return _print(_client(config, args.dry_run).pending_decisions())

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

    if args.command == "connectors":
        if args.connectors_command == "list":
            return _print({"ok": True, "status": "scaffold", "message": "Remote connector catalog is not wired yet."})
        if args.connectors_command == "registered":
            return _print({"ok": True, "items": config.connector_registry})
        if args.connectors_command == "test":
            connector = next((item for item in config.connector_registry if item.get("id") == args.connector_id), None)
            return _print({"ok": connector is not None, "item": connector})
        if args.connectors_command == "add":
            config.connector_registry.append(
                {
                    "id": args.id,
                    "url": args.url,
                    "auth": args.auth,
                    "token": args.token or "",
                }
            )
            save_config(config)
            return _print({"ok": True, "status": "saved", "connector_id": args.id})
        if args.connectors_command == "remove":
            before = len(config.connector_registry)
            config.connector_registry = [
                item for item in config.connector_registry if item.get("id") != args.connector_id
            ]
            save_config(config)
            return _print(
                {
                    "ok": True,
                    "status": "removed" if len(config.connector_registry) < before else "not_found",
                    "connector_id": args.connector_id,
                }
            )

    if args.command == "contracts":
        if args.contracts_command == "list":
            return _print(_client(config, args.dry_run).list_contracts())
        if args.contracts_command == "pull":
            return _print(_client(config, args.dry_run).pull_contract(args.contract_id))

    if args.command == "usage":
        return _print({"ok": True, "status": "scaffold", "from": args.__dict__.get("from"), "to": args.to})

    if args.command == "plan":
        return _print({"ok": True, "status": "scaffold", "message": "Plan endpoint is not wired yet."})

    if args.command == "cost":
        return _print({"ok": True, "status": "scaffold", "run_id": args.run_id})

    if args.command == "runs":
        if args.runs_command == "list":
            return _print(_client(config, args.dry_run).list_runs())

    if args.command == "serve":
        return _print({"ok": True, "status": "scaffold", "mode": args.mode, "message": "MCP/native tool mode is the next major slice."})

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
