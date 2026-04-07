from __future__ import annotations

import hashlib
import json
from pathlib import Path


REQUIRED_PACKAGE_FILES = [
    "source_contract_package_v0.json",
    "runtime_manifest_v0.json",
    "policy_calibration_v0.json",
    "input_model_v0.json",
    "verification_model_v0.json",
    "README.md",
    "execution_note.md",
]


def package_root(path: str | Path) -> Path:
    root = Path(path).expanduser().resolve()
    if root.is_file():
        return root.parent
    return root


def validate_contract_package(path: str | Path) -> dict[str, object]:
    root = package_root(path)
    missing = [name for name in REQUIRED_PACKAGE_FILES if not (root / name).exists()]
    parsed_files: dict[str, object] = {}
    json_errors: list[dict[str, str]] = []
    for name in REQUIRED_PACKAGE_FILES:
        file_path = root / name
        if not file_path.exists() or not name.endswith(".json"):
            continue
        try:
            parsed_files[name] = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception as exc:  # pragma: no cover - surfaced to CLI
            json_errors.append({"file": name, "error": str(exc)})

    source = parsed_files.get("source_contract_package_v0.json", {})
    runtime = parsed_files.get("runtime_manifest_v0.json", {})
    calibration = parsed_files.get("policy_calibration_v0.json", {})

    checks = {
        "contract_id_present": isinstance(source, dict) and isinstance(source.get("contract_id"), str),
        "version_present": isinstance(source, dict) and isinstance(source.get("version"), str),
        "runtime_process_contract_ref_present": isinstance(runtime, dict)
        and isinstance(runtime.get("process_contract_ref"), str),
        "runtime_executor_present": isinstance(runtime, dict) and isinstance(runtime.get("executor_ref"), str),
        "calibration_executor_present": isinstance(calibration, dict)
        and isinstance(calibration.get("executor_ref"), str),
    }

    return {
        "ok": not missing and not json_errors and all(checks.values()),
        "root": str(root),
        "missing_files": missing,
        "json_errors": json_errors,
        "checks": checks,
    }


def inspect_contract_package(path: str | Path) -> dict[str, object]:
    root = package_root(path)
    source = json.loads((root / "source_contract_package_v0.json").read_text(encoding="utf-8"))
    runtime = json.loads((root / "runtime_manifest_v0.json").read_text(encoding="utf-8"))
    calibration = json.loads((root / "policy_calibration_v0.json").read_text(encoding="utf-8"))
    return {
        "root": str(root),
        "contract_id": source.get("contract_id"),
        "version": source.get("version"),
        "title": source.get("title"),
        "summary": source.get("summary"),
        "service_bindings": source.get("service_bindings", []),
        "required_inputs": source.get("required_inputs", []),
        "process_contract_ref": runtime.get("process_contract_ref"),
        "runtime_execution_mode": runtime.get("execution_mode"),
        "executor_ref": runtime.get("executor_ref"),
        "calibration_id": calibration.get("calibration_id"),
        "calibration_execution_mode": calibration.get("engine15_execution_mode"),
    }


def load_package_projection(path: str | Path) -> dict[str, object]:
    root = package_root(path)
    return {
        "source_contract_package": json.loads((root / "source_contract_package_v0.json").read_text(encoding="utf-8")),
        "runtime_manifest": json.loads((root / "runtime_manifest_v0.json").read_text(encoding="utf-8")),
        "policy_calibration": json.loads((root / "policy_calibration_v0.json").read_text(encoding="utf-8")),
    }


def build_package_ref(path: str | Path) -> dict[str, str]:
    root = package_root(path)
    source_path = root / "source_contract_package_v0.json"
    source_payload = json.loads(source_path.read_text(encoding="utf-8"))
    contract_id = str(source_payload["contract_id"])
    version = str(source_payload["version"])
    hash_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest()
    return {
        "package_id": contract_id,
        "version": version,
        "hash_sha256": hash_sha256,
        "source_uri": str(source_path),
    }
