from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from .contracts import package_root


TEMPLATE_ROOT = Path("D:/Projects_MOVA/_mova_meta/templates/contract_package_v0")
SDK_VERSION = "0.1.0"


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or "custom_contract"


def _title_from_intent(intent: str) -> str:
    cleaned = re.sub(r"\s+", " ", intent).strip()
    if not cleaned:
        return "Custom Contract"
    return " ".join(word.capitalize() if word.islower() else word for word in cleaned[:80].split(" "))


def _load_template_json(name: str) -> dict[str, object]:
    return json.loads((TEMPLATE_ROOT / name).read_text(encoding="utf-8"))


def _render_readme(title: str, summary: str, required_inputs: list[str], service_bindings: list[str]) -> str:
    return (
        f"# {title}\n\n"
        f"{summary}\n\n"
        "## Candidate Status\n\n"
        "- This package is a candidate contract generated locally in Forge.\n"
        "- It is not frozen for production execution.\n"
        "- Next step: hand off into MOVA authoring/lab flow.\n\n"
        "## Required Inputs\n\n"
        + "\n".join(f"- `{name}`" for name in required_inputs)
        + "\n\n## Service Bindings\n\n"
        + "\n".join(f"- `{name}`" for name in service_bindings)
        + "\n"
    )


def _render_execution_note(
    title: str,
    mode: str,
    service_bindings: list[str],
    unresolved_gaps: list[str],
) -> str:
    lines = [
        f"# Execution Note — {title}",
        "",
        f"- Source execution mode: `{mode}`",
        "- This package is a candidate and should be tested in the MOVA lab before freeze.",
        "- External dependencies declared for this package:",
    ]
    lines.extend(f"  - `{binding}`" for binding in service_bindings)
    if unresolved_gaps:
        lines.append("- Unresolved gaps for the next platform step:")
        lines.extend(f"  - `{item}`" for item in unresolved_gaps)
    lines.append("")
    return "\n".join(lines)


def _build_input_model(required_inputs: list[str]) -> dict[str, object]:
    properties = {name: {"type": "string", "description": f"Business input `{name}`"} for name in required_inputs}
    return {
        "type": "object",
        "required": required_inputs,
        "properties": properties,
        "additionalProperties": False,
    }


def _build_verification_model(verification_codes: list[str], terminal_outcomes: list[str]) -> dict[str, object]:
    mapped: list[dict[str, object]] = []
    for index, code in enumerate(verification_codes):
        mapped.append(
            {
                "code": code,
                "maps_to": terminal_outcomes[min(index, len(terminal_outcomes) - 1)],
                "severity": "info" if index == 0 else "warning",
            }
        )
    return {"verification_codes": mapped}


def _classify_intent(intent: str) -> dict[str, object]:
    text = intent.lower()
    contract_class = "custom"
    required_inputs = ["subject_id"]
    optional_inputs: list[str] = []
    service_bindings = ["connector.user.required"]
    source_execution_mode = "ai_assisted"
    engine15_execution_mode = "DRAFT_REVIEW"
    terminal_outcomes = ["COMPLETED", "FAILED"]
    verification_codes = ["SUCCESS", "FAILED"]
    unresolved_gaps = [
        "Policy and runtime wiring must be validated in the platform.",
        "Connector bindings must be checked against real owner context.",
    ]

    if "invoice" in text or "iban" in text or "vendor" in text:
        contract_class = "finance"
        required_inputs = ["file_url"]
        optional_inputs = ["vendor_reference", "currency"]
        service_bindings = ["connector.document.ocr", "connector.finance.readonly"]
        terminal_outcomes = ["APPROVED", "REJECTED", "NEEDS_REVIEW"]
        verification_codes = ["INVOICE_EXTRACTED", "IBAN_VERIFIED", "REVIEW_REQUIRED"]
    elif "ticket" in text or "helpdesk" in text or "support" in text:
        contract_class = "ticket"
        required_inputs = ["title", "summary"]
        optional_inputs = ["customer_id", "priority"]
        service_bindings = ["connector.helpdesk.api"]
        terminal_outcomes = ["TRIAGED", "ESCALATED", "REJECTED"]
        verification_codes = ["ROUTE_MATCH", "ESCALATION_REQUIRED", "INSUFFICIENT_DATA"]
    elif "crm" in text or "lead" in text or "sales" in text:
        contract_class = "crm"
        required_inputs = ["subject_id"]
        optional_inputs = ["crm_record_id", "owner_email"]
        service_bindings = ["connector.crm.api"]
        terminal_outcomes = ["UPDATED", "QUEUED", "FAILED"]
        verification_codes = ["CRM_UPDATED", "SYNC_DEFERRED", "SYNC_FAILED"]

    if "approval" in text or "approve" in text or "human" in text:
        source_execution_mode = "human_gated"
        if "connector.human.review" not in service_bindings:
            service_bindings.append("connector.human.review")
    elif "deterministic" in text:
        source_execution_mode = "deterministic"
        engine15_execution_mode = "SAFE_INTERNAL"
    elif "read only" in text or "read-only" in text:
        engine15_execution_mode = "LIVE_READ_ONLY"

    return {
        "contract_class": contract_class,
        "required_inputs": required_inputs,
        "optional_inputs": optional_inputs,
        "service_bindings": service_bindings,
        "source_execution_mode": source_execution_mode,
        "engine15_execution_mode": engine15_execution_mode,
        "terminal_outcomes": terminal_outcomes,
        "verification_codes": verification_codes,
        "unresolved_gaps": unresolved_gaps,
    }


@dataclass
class ForgeSession:
    session_id: str
    intent: str
    source_path: str | None
    crystallized_intent: dict[str, object]
    contract_shape: dict[str, object]
    package_preview: dict[str, object]

    def candidate_summary(self) -> dict[str, object]:
        source_contract = self.package_preview["source_contract_package_v0.json"]
        runtime_manifest = self.package_preview["runtime_manifest_v0.json"]
        return {
            "session_id": self.session_id,
            "intent": self.intent,
            "contract_id": self.contract_shape["contract_id"],
            "contract_class": self.contract_shape["contract_class"],
            "source_execution_mode": self.contract_shape["source_execution_mode"],
            "engine15_execution_mode": self.contract_shape["engine15_execution_mode"],
            "required_inputs": list(self.contract_shape["required_inputs"]),
            "service_bindings": list(self.contract_shape["service_bindings"]),
            "visibility": source_contract.get("visibility"),
            "runtime_status": runtime_manifest.get("status"),
            "unresolved_gaps": list(self.crystallized_intent.get("unresolved_gaps", [])),
        }

    def to_local_candidate_handoff(
        self,
        *,
        target: str = "authoring",
        actor_id: str | None = None,
        owner_ref: str | None = None,
        tenant_ref: str | None = None,
    ) -> dict[str, object]:
        intent_context = self.crystallized_intent.get("intent_context", {})
        return {
            "env_type": "sdk_local_candidate_handoff_v1",
            "handoff_id": f"handoff_{uuid4().hex}",
            "created_at": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "source": {
                "sdk_name": "mova-tool-sdk",
                "sdk_version": SDK_VERSION,
                "calibration_mode": "local_manual",
            },
            "actor_context": {
                "actor_id": actor_id or "actor.local",
                "owner_ref": owner_ref or "org.user.local",
                "tenant_ref": tenant_ref or "tenant.local",
            },
            "intent_context": {
                "raw_intent_text": self.intent,
                "goal_description": intent_context.get("goal_description", ""),
                "verification_criteria": intent_context.get("verification_criteria", []),
                "invariants": intent_context.get("invariants", []),
                "unresolved_gaps": self.crystallized_intent.get("unresolved_gaps", []),
            },
            "candidate_package": {
                "source_contract_package_v0": self.package_preview["source_contract_package_v0.json"],
                "runtime_manifest_v0": self.package_preview["runtime_manifest_v0.json"],
                "policy_calibration_v0": self.package_preview["policy_calibration_v0.json"],
                "input_model_v0": self.package_preview["input_model_v0.json"],
                "verification_model_v0": self.package_preview["verification_model_v0.json"],
            },
            "handoff": {
                "target": target,
                "intent": "create_candidate_draft" if target == "authoring" else "test_candidate_in_lab",
            },
        }

    def generate_package(self, output_path: str | Path) -> dict[str, object]:
        root = Path(output_path).expanduser().resolve()
        root.mkdir(parents=True, exist_ok=True)
        (root / "fixtures").mkdir(exist_ok=True)

        files = {
            "README.md": self.package_preview["README.md"],
            "execution_note.md": self.package_preview["execution_note.md"],
            "input_model_v0.json": json.dumps(self.package_preview["input_model_v0.json"], ensure_ascii=False, indent=2),
            "verification_model_v0.json": json.dumps(
                self.package_preview["verification_model_v0.json"], ensure_ascii=False, indent=2
            ),
            "policy_calibration_v0.json": json.dumps(
                self.package_preview["policy_calibration_v0.json"], ensure_ascii=False, indent=2
            ),
            "runtime_manifest_v0.json": json.dumps(
                self.package_preview["runtime_manifest_v0.json"], ensure_ascii=False, indent=2
            ),
            "source_contract_package_v0.json": json.dumps(
                self.package_preview["source_contract_package_v0.json"], ensure_ascii=False, indent=2
            ),
            "validate_contract_package.py": (TEMPLATE_ROOT / "validate_contract_package.py").read_text(encoding="utf-8"),
            "fixtures/README.md": (TEMPLATE_ROOT / "fixtures" / "README.md").read_text(encoding="utf-8"),
        }

        for relative_path, contents in files.items():
            target = root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(contents, encoding="utf-8")

        handoff_payload = self.to_local_candidate_handoff()
        (root / "sdk_local_candidate_handoff_v1.json").write_text(
            json.dumps(handoff_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return {
            "ok": True,
            "status": "generated",
            "output_path": str(root),
            "contract_id": self.contract_shape["contract_id"],
            "files": sorted([*files.keys(), "sdk_local_candidate_handoff_v1.json"]),
        }


def start_forge(intent: str | None = None, source_path: str | None = None) -> ForgeSession:
    seeded_contract: dict[str, object] = {}
    if source_path:
        root = package_root(source_path)
        source_file = root / "source_contract_package_v0.json"
        if source_file.exists():
            seeded_contract = json.loads(source_file.read_text(encoding="utf-8"))

    raw_intent = intent or str(seeded_contract.get("summary") or seeded_contract.get("title") or "custom contract")
    shaping = _classify_intent(raw_intent)
    title = str(seeded_contract.get("title") or _title_from_intent(raw_intent))
    slug = str(seeded_contract.get("contract_id") or f"contract.{_slugify(title)}.v1")
    process_ref = f"pkg_{_slugify(title)}_v1_candidate"
    executor_ref = f"runtime_executor.{_slugify(title)}_v1"
    required_inputs = list(seeded_contract.get("required_inputs") or shaping["required_inputs"])
    optional_inputs = list(seeded_contract.get("optional_inputs") or shaping["optional_inputs"])
    service_bindings = list(seeded_contract.get("service_bindings") or shaping["service_bindings"])
    summary = str(seeded_contract.get("summary") or f"Candidate contract generated from the business intent: {raw_intent.strip()}.")
    timestamp = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    crystallized_intent = {
        "status": "candidate_ready",
        "raw_intent": raw_intent,
        "intent_context": {
            "goal_description": "Turn the calibrated business task into a candidate contract package for platform testing.",
            "verification_criteria": [
                "The package validates structurally.",
                "The package is suitable for authoring/lab handoff.",
            ],
            "invariants": ["Use canonical contract_package_v0 structure."],
        },
        "unresolved_gaps": list(shaping["unresolved_gaps"]),
        "recommendation": "Hand this candidate into MOVA authoring/lab flow for test runs and hardening.",
    }

    contract_shape = {
        "title": title,
        "contract_id": slug,
        "process_contract_ref": process_ref,
        "contract_class": str(seeded_contract.get("contract_class") or shaping["contract_class"]),
        "source_execution_mode": str(seeded_contract.get("execution_mode") or shaping["source_execution_mode"]),
        "engine15_execution_mode": str(shaping["engine15_execution_mode"]),
        "executor_ref": executor_ref,
        "required_inputs": required_inputs,
        "optional_inputs": optional_inputs,
        "service_bindings": service_bindings,
        "terminal_outcomes": list(shaping["terminal_outcomes"]),
        "verification_codes": list(shaping["verification_codes"]),
    }

    source_contract = deepcopy(_load_template_json("source_contract_package_v0.json"))
    source_contract.update(
        {
            "contract_id": slug,
            "version": str(seeded_contract.get("version") or "1.0.0"),
            "title": title,
            "summary": summary,
            "contract_class": contract_shape["contract_class"],
            "intent_ref": f"intent.{_slugify(title)}.v1",
            "policy_ref": f"policy.{_slugify(title)}.v1",
            "transition_rule_ref": f"transition.{_slugify(title)}.v1",
            "verification_profile_ref": f"verification.{_slugify(title)}.v1",
            "execution_mode": contract_shape["source_execution_mode"],
            "service_bindings": service_bindings,
            "required_inputs": required_inputs,
            "optional_inputs": optional_inputs,
            "publisher_ref": "org.user.local",
            "visibility": "private",
            "status": "candidate",
            "applicability": [raw_intent],
            "not_applicable": ["Unreviewed production execution"],
            "created_at": timestamp,
            "updated_at": timestamp,
        }
    )

    runtime_manifest = deepcopy(_load_template_json("runtime_manifest_v0.json"))
    runtime_manifest.update(
        {
            "process_contract_ref": process_ref,
            "runtime_handler": f"runtime_handler.{_slugify(title)}_v1",
            "executor_ref": executor_ref,
            "execution_mode": contract_shape["engine15_execution_mode"],
            "execution_capable_target": False,
            "input_model_ref": f"packages/contracts/{process_ref}/input_model_v0.json",
            "verification_model_ref": f"packages/contracts/{process_ref}/verification_model_v0.json",
            "capabilities": {
                "self_contained": False,
                "external_state": len(service_bindings) > 0,
                "mutation": False,
                "human_gated": contract_shape["source_execution_mode"] == "human_gated",
                "safe_internal_only": contract_shape["engine15_execution_mode"] == "SAFE_INTERNAL",
                "live_read_only": contract_shape["engine15_execution_mode"] == "LIVE_READ_ONLY",
            },
            "terminal_outcomes": contract_shape["terminal_outcomes"],
            "status": "CANDIDATE",
        }
    )

    policy_calibration = deepcopy(_load_template_json("policy_calibration_v0.json"))
    policy_calibration.update(
        {
            "calibration_id": f"{process_ref}_policy_calibration_v0",
            "source_contract_id": slug,
            "source_execution_mode": contract_shape["source_execution_mode"],
            "engine15_execution_mode": contract_shape["engine15_execution_mode"],
            "executor_ref": executor_ref,
            "mapping": {
                code: contract_shape["terminal_outcomes"][min(index, len(contract_shape["terminal_outcomes"]) - 1)]
                for index, code in enumerate(contract_shape["verification_codes"])
            },
            "rationale": [
                "This is a local candidate package.",
                "Freeze and production execution posture must be hardened through the platform lab flow.",
            ],
        }
    )

    package_preview = {
        "README.md": _render_readme(title, summary, required_inputs, service_bindings),
        "execution_note.md": _render_execution_note(
            title,
            contract_shape["source_execution_mode"],
            service_bindings,
            list(shaping["unresolved_gaps"]),
        ),
        "input_model_v0.json": _build_input_model(required_inputs),
        "verification_model_v0.json": _build_verification_model(
            contract_shape["verification_codes"],
            contract_shape["terminal_outcomes"],
        ),
        "policy_calibration_v0.json": policy_calibration,
        "runtime_manifest_v0.json": runtime_manifest,
        "source_contract_package_v0.json": source_contract,
    }

    return ForgeSession(
        session_id=f"forge_{uuid4().hex}",
        intent=raw_intent,
        source_path=source_path,
        crystallized_intent=crystallized_intent,
        contract_shape=contract_shape,
        package_preview=package_preview,
    )
