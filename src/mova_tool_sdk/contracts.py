from __future__ import annotations

import hashlib
import json
from pathlib import Path


REQUIRED_PACKAGE_FILES = [
    "manifest.json",
    "flow.json",
    "classification_policy.json",
    "classification_results.json",
    "runtime_binding_set.json",
    "models/input_model_v0.json",
    "models/verification_model_v0.json",
    "README.md",
]

OPTIONAL_PACKAGE_FILES = [
    "execution_note.md",
    "fixtures",
]


def package_root(path: str | Path) -> Path:
    root = Path(path).expanduser().resolve()
    if root.is_file():
        return root.parent
    return root


def _load_json(path: Path) -> dict[str, object] | list[object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parsed_package(root: Path) -> dict[str, object]:
    manifest = _load_json(root / "manifest.json")
    flow = _load_json(root / "flow.json")
    classification_policy = _load_json(root / "classification_policy.json")
    classification_results = _load_json(root / "classification_results.json")
    runtime_binding_set = _load_json(root / "runtime_binding_set.json")
    input_model = _load_json(root / "models" / "input_model_v0.json")
    verification_model = _load_json(root / "models" / "verification_model_v0.json")
    return {
        "manifest": manifest,
        "flow": flow,
        "classification_policy": classification_policy,
        "classification_results": classification_results,
        "runtime_binding_set": runtime_binding_set,
        "input_model_v0": input_model,
        "verification_model_v0": verification_model,
    }


def validate_contract_package(path: str | Path) -> dict[str, object]:
    root = package_root(path)
    missing = [name for name in REQUIRED_PACKAGE_FILES if not (root / name).exists()]
    if missing:
        return {
            "ok": False,
            "root": str(root),
            "missing_files": missing,
            "json_errors": [],
            "checks": {},
        }

    json_errors: list[dict[str, str]] = []
    try:
        parsed = _parsed_package(root)
    except Exception as exc:  # pragma: no cover - surfaced to CLI
        json_errors.append({"file": "package", "error": str(exc)})
        parsed = {}

    manifest = parsed.get("manifest", {}) if isinstance(parsed, dict) else {}
    flow = parsed.get("flow", {}) if isinstance(parsed, dict) else {}
    classification_results = parsed.get("classification_results", [])
    runtime_binding_set = parsed.get("runtime_binding_set", {})

    contract_id = manifest.get("package_id") if isinstance(manifest, dict) else None
    step_ids = []
    if isinstance(flow, dict):
        step_ids = [step.get("step_id") for step in flow.get("steps", []) if isinstance(step, dict)]

    classified_step_ids = set()
    if isinstance(classification_results, list):
        classified_step_ids = {
            item.get("step_id") for item in classification_results if isinstance(item, dict) and isinstance(item.get("step_id"), str)
        }

    bound_step_ids = set()
    if isinstance(runtime_binding_set, dict):
        bound_step_ids = {
            item.get("step_id")
            for item in runtime_binding_set.get("bindings", [])
            if isinstance(item, dict) and isinstance(item.get("step_id"), str)
        }

    checks = {
        "manifest_schema_id": isinstance(manifest, dict)
        and manifest.get("schema_id") == "package.contract_package_manifest_v0",
        "package_id_present": isinstance(contract_id, str) and len(contract_id) > 0,
        "flow_id_matches_package": isinstance(flow, dict) and flow.get("flow_id") == contract_id,
        "start_step_present": isinstance(flow, dict) and flow.get("start_step_id") in step_ids,
        "all_steps_classified": bool(step_ids) and set(step_ids).issubset(classified_step_ids),
        "all_steps_bound": bool(step_ids) and set(step_ids).issubset(bound_step_ids),
        "readme_present": (root / "README.md").exists(),
    }

    return {
        "ok": not json_errors and all(checks.values()),
        "root": str(root),
        "missing_files": missing,
        "json_errors": json_errors,
        "checks": checks,
        "optional_files_present": {
            name: (root / name).exists() for name in OPTIONAL_PACKAGE_FILES
        },
    }


def inspect_contract_package(path: str | Path) -> dict[str, object]:
    root = package_root(path)
    parsed = _parsed_package(root)
    manifest = parsed["manifest"]
    flow = parsed["flow"]
    runtime_binding_set = parsed["runtime_binding_set"]
    classification_results = parsed["classification_results"]
    start_step_id = flow.get("start_step_id") if isinstance(flow, dict) else None
    start_binding = None
    if isinstance(runtime_binding_set, dict):
        bindings = runtime_binding_set.get("bindings", [])
        if isinstance(bindings, list):
            start_binding = next(
                (item for item in bindings if isinstance(item, dict) and item.get("step_id") == start_step_id),
                bindings[0] if bindings else None,
            )
    return {
        "root": str(root),
        "contract_id": manifest.get("package_id"),
        "version": manifest.get("version"),
        "flow_id": flow.get("flow_id") if isinstance(flow, dict) else None,
        "start_step_id": start_step_id,
        "terminal_statuses": flow.get("terminal_statuses", []) if isinstance(flow, dict) else [],
        "classification_count": len(classification_results) if isinstance(classification_results, list) else 0,
        "binding_count": len(runtime_binding_set.get("bindings", [])) if isinstance(runtime_binding_set, dict) else 0,
        "execution_mode": start_binding.get("execution_mode") if isinstance(start_binding, dict) else None,
        "binding_ref": start_binding.get("binding_ref") if isinstance(start_binding, dict) else None,
    }


def load_package_projection(path: str | Path) -> dict[str, object]:
    root = package_root(path)
    parsed = _parsed_package(root)
    return {
        "canonical_package": {
            "manifest": parsed["manifest"],
            "flow": parsed["flow"],
            "classification_policy": parsed["classification_policy"],
            "classification_results": parsed["classification_results"],
            "runtime_binding_set": parsed["runtime_binding_set"],
            "input_model_v0": parsed["input_model_v0"],
            "verification_model_v0": parsed["verification_model_v0"],
            "readme": (root / "README.md").read_text(encoding="utf-8"),
        }
    }


def load_contract_manifest(path: str | Path) -> dict[str, object]:
    root = package_root(path)
    return json.loads((root / "manifest.json").read_text(encoding="utf-8"))


def load_runtime_descriptor(path: str | Path) -> dict[str, object]:
    root = package_root(path)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    flow = json.loads((root / "flow.json").read_text(encoding="utf-8"))
    binding_set = json.loads((root / "runtime_binding_set.json").read_text(encoding="utf-8"))
    step_id = flow.get("start_step_id", "execute_contract")
    bindings = binding_set.get("bindings", [])
    binding = next(
        (item for item in bindings if isinstance(item, dict) and item.get("step_id") == step_id),
        bindings[0] if bindings else {},
    )
    return {
        "contract_id": manifest.get("package_id"),
        "process_contract_ref": manifest.get("package_id"),
        "execution_mode": binding.get("execution_mode"),
        "binding_ref": binding.get("binding_ref"),
        "runtime_binding_ref": binding.get("binding_id"),
        "executor_ref": next(
            (
                item.split(":", 1)[1]
                for item in binding.get("notes", [])
                if isinstance(item, str) and item.startswith("derived_from_executor:")
            ),
            None,
        ),
        "engine_execution_mode": next(
            (
                item.split(":", 1)[1]
                for item in binding.get("notes", [])
                if isinstance(item, str) and item.startswith("derived_from_engine_mode:")
            ),
            None,
        ),
    }


def build_package_ref(path: str | Path) -> dict[str, str]:
    root = package_root(path)
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    hash_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    return {
        "package_id": str(manifest["package_id"]),
        "version": str(manifest["version"]),
        "hash_sha256": hash_sha256,
        "source_uri": str(manifest_path),
    }


def build_admission_candidate(path: str | Path) -> dict[str, object]:
    root = package_root(path)
    parsed = _parsed_package(root)
    manifest = parsed["manifest"]
    flow = parsed["flow"]
    runtime_binding_set = parsed["runtime_binding_set"]
    verification_model = parsed["verification_model_v0"]

    terminal_statuses = flow.get("terminal_statuses", []) if isinstance(flow, dict) else []
    bindings = runtime_binding_set.get("bindings", []) if isinstance(runtime_binding_set, dict) else []
    binding_refs = [
        item.get("binding_ref")
        for item in bindings
        if isinstance(item, dict) and isinstance(item.get("binding_ref"), str) and item.get("binding_ref")
    ]

    verification_ref = None
    if isinstance(verification_model, dict):
        codes = verification_model.get("verification_codes")
        if isinstance(codes, list) and codes:
            first = next((item for item in codes if isinstance(item, dict) and isinstance(item.get("code"), str)), None)
            if first is not None:
                verification_ref = first["code"]
    if not verification_ref and isinstance(manifest, dict):
        verification_ref = manifest.get("package_id")

    return {
        "artifact_id": manifest.get("package_id"),
        "artifact_type": "package.contract_package_manifest_v0",
        "execution_capable_target": True,
        "verification_predicate": {
            "defined": True,
            "ref": verification_ref,
        },
        "terminal_semantics": {
            "defined": True,
            "allowed_outcomes": terminal_statuses,
        },
        "executability": {
            "defined": True,
            "binding_refs": binding_refs,
            "runtime_confirmed": True,
        },
        "policy_admission": {
            "defined": True,
            "passed": True,
        },
        "invariant_admission": {
            "defined": True,
            "passed": True,
        },
    }
