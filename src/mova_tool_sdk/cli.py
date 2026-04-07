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
