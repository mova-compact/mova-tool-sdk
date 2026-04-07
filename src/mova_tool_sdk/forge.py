from __future__ import annotations

import json
import re
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from .config import mova_home
from .contracts import package_root


TEMPLATE_ROOT = Path("D:/Projects_MOVA/_mova_meta/templates/contract_package_v0")
FORGE_SESSION_DIR = mova_home() / "forge_sessions"
STEP_DEFINITIONS = [
    ("problem_framing", "Determine what kind of business problem is being converted into a contract."),
    ("outcome", "State the exact business result the contract must produce."),
    ("reality", "Clarify what data and operating reality the contract can rely on."),
    ("strategy", "Choose how the contract should solve the task."),
    ("verification", "Define how success and failure are verified."),
    ("constraints", "Make non-negotiable boundaries explicit."),
    ("decision_rights", "Separate human decisions from system autonomy."),
    ("uncertainty", "Declare what remains uncertain or review-first."),
    ("commitment", "Confirm authorship and responsibility for the generated package."),
]
STEP_OPTIONS = {
    "problem_framing": [
        "result-definition",
        "diagnosis",
        "planning",
        "selection-filtering",
        "coordination",
    ],
    "outcome": [
        "artifact_creation",
        "state_change",
        "behavior_change",
        "decision_preparation",
    ],
    "reality": [
        "goal_only",
        "goal_plus_current_state",
        "goal_plus_constraints",
        "goal_plus_evidence",
    ],
    "strategy": [
        "rigid_plan",
        "adaptive_feedback",
        "deficit_first",
        "outcome_backwards",
    ],
    "verification": [
        "artifact_exists",
        "behavior_changed",
        "external_review",
        "combined_verification",
    ],
    "constraints": [
        "time",
        "resources",
        "legal_boundary",
        "risk_tolerance",
        "scope_boundary",
    ],
    "decision_rights": [
        "human_decides_criteria_system_executes",
        "human_approves_final_only",
        "system_filters_human_selects",
        "system_local_autonomy_with_guardrails",
    ],
    "uncertainty": [
        "input_incompleteness",
        "environment_instability",
        "subjective_evaluation",
        "resource_unpredictability",
    ],
    "commitment": [
        "keep_private",
        "register_private_later",
        "publish_public_later",
    ],
}
CHOICE_ALIASES = {
    "problem_framing": {
        "result": "result-definition",
        "selection": "selection-filtering",
    },
    "outcome": {
        "artifact": "artifact_creation",
        "state": "state_change",
        "behavior": "behavior_change",
        "decision": "decision_preparation",
    },
    "reality": {
        "goal-state": "goal_plus_current_state",
        "goal-constraints": "goal_plus_constraints",
        "goal-evidence": "goal_plus_evidence",
    },
    "strategy": {
        "rigid": "rigid_plan",
        "adaptive": "adaptive_feedback",
        "deficit": "deficit_first",
        "backwards": "outcome_backwards",
    },
    "verification": {
        "artifact": "artifact_exists",
        "behavior": "behavior_changed",
        "review": "external_review",
        "combined": "combined_verification",
    },
    "constraints": {
        "legal": "legal_boundary",
        "risk": "risk_tolerance",
        "scope": "scope_boundary",
    },
    "decision_rights": {
        "human-criteria": "human_decides_criteria_system_executes",
        "human-final": "human_approves_final_only",
        "system-filters": "system_filters_human_selects",
        "guardrails": "system_local_autonomy_with_guardrails",
    },
    "uncertainty": {
        "input": "input_incompleteness",
        "environment": "environment_instability",
        "subjective": "subjective_evaluation",
        "resource": "resource_unpredictability",
    },
    "commitment": {
        "private": "keep_private",
        "register-private": "register_private_later",
        "public": "publish_public_later",
    },
}


def _choice_label(choice: str) -> str:
    return choice.replace("_", " ").replace("-", " ").strip().capitalize()


def _aliases_for_choice(step_id: str, choice: str) -> list[str]:
    aliases = []
    for alias, target in CHOICE_ALIASES.get(step_id, {}).items():
        if target == choice:
            aliases.append(alias)
    return aliases


def build_step_options(step_id: str, options: list[str]) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for index, choice in enumerate(options, start=1):
        items.append(
            {
                "index": index,
                "value": choice,
                "label": _choice_label(choice),
                "aliases": _aliases_for_choice(step_id, choice),
            }
        )
    return items


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", value.strip().lower())
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return normalized or "custom_contract"


def _title_from_intent(intent: str) -> str:
    cleaned = re.sub(r"\s+", " ", intent).strip()
    if not cleaned:
        return "Custom Contract"
    title_words = cleaned[:80].split(" ")
    return " ".join(word.capitalize() if word.islower() else word for word in title_words)


def _load_template_json(name: str) -> dict[str, object]:
    return json.loads((TEMPLATE_ROOT / name).read_text(encoding="utf-8"))


def _render_readme(title: str, summary: str, required_inputs: list[str], service_bindings: list[str]) -> str:
    return (
        f"# {title}\n\n"
        f"{summary}\n\n"
        "## When to use\n\n"
        "- Use this contract when the business task matches the calibrated intent.\n\n"
        "## Required inputs\n\n"
        + "\n".join(f"- `{name}`" for name in required_inputs)
        + "\n\n## Required service bindings\n\n"
        + "\n".join(f"- `{name}`" for name in service_bindings)
        + "\n"
    )


def _render_execution_note(title: str, mode: str, service_bindings: list[str]) -> str:
    return (
        f"# Execution Note — {title}\n\n"
        f"- Source execution mode: `{mode}`\n"
        "- This package was generated by the first Forge slice and should be reviewed before publication.\n"
        "- Automatic execution boundaries and human gates must be refined during contract hardening.\n"
        "- External dependencies declared for this package:\n"
        + "\n".join(f"  - `{binding}`" for binding in service_bindings)
        + "\n"
    )


def _render_execution_note_with_context(
    title: str,
    mode: str,
    service_bindings: list[str],
    constraints: list[str],
    uncertainty: list[str],
) -> str:
    lines = [
        f"# Execution Note — {title}",
        "",
        f"- Source execution mode: `{mode}`",
        "- This package was generated by Forge and should be reviewed before publication.",
        "- Automatic execution boundaries and human gates must be refined during contract hardening.",
        "- External dependencies declared for this package:",
    ]
    lines.extend(f"  - `{binding}`" for binding in service_bindings)
    if constraints:
        lines.append("- Active constraints:")
        lines.extend(f"  - `{item}`" for item in constraints)
    if uncertainty:
        lines.append("- Remaining uncertainty:")
        lines.extend(f"  - `{item}`" for item in uncertainty)
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
        outcome = terminal_outcomes[min(index, len(terminal_outcomes) - 1)]
        severity = "info" if index == 0 else "warning" if index < len(verification_codes) - 1 else "error"
        mapped.append({"code": code, "maps_to": outcome, "severity": severity})
    return {
        "verification_codes": mapped
    }


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

    if "invoice" in text or "iban" in text or "vendor" in text:
        contract_class = "finance"
        required_inputs = ["file_url"]
        optional_inputs = ["vendor_reference", "currency"]
        service_bindings = ["connector.document.ocr", "connector.finance.readonly"]
        if "approval" in text or "approve" in text:
            service_bindings.append("connector.human.review")
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
    elif "logistics" in text or "shipment" in text or "delivery" in text:
        contract_class = "logistics"
        required_inputs = ["shipment_id"]
        optional_inputs = ["tracking_number"]
        service_bindings = ["connector.logistics.api"]
        terminal_outcomes = ["ROUTED", "HELD", "FAILED"]
        verification_codes = ["ROUTE_VALID", "HOLD_REQUIRED", "ROUTE_FAILED"]

    if "approval" in text or "approve" in text or "human" in text:
        source_execution_mode = "human_gated"
        engine15_execution_mode = "DRAFT_REVIEW"
        if "connector.human.review" not in service_bindings:
            service_bindings.append("connector.human.review")
    elif "read only" in text or "read-only" in text:
        engine15_execution_mode = "LIVE_READ_ONLY"
    elif "deterministic" in text:
        source_execution_mode = "deterministic"
        engine15_execution_mode = "SAFE_INTERNAL"

    return {
        "contract_class": contract_class,
        "required_inputs": required_inputs,
        "optional_inputs": optional_inputs,
        "service_bindings": service_bindings,
        "source_execution_mode": source_execution_mode,
        "engine15_execution_mode": engine15_execution_mode,
        "terminal_outcomes": terminal_outcomes,
        "verification_codes": verification_codes,
    }


def normalize_choice(step_id: str, raw_choice: str, options: list[str]) -> str:
    choice = raw_choice.strip()
    if not choice:
        raise ValueError("choice is empty")
    if choice.isdigit():
        index = int(choice) - 1
        if 0 <= index < len(options):
            return options[index]
    if choice in options:
        return choice
    normalized = choice.replace(" ", "_").replace("-", "_")
    for option in options:
        if option.replace("-", "_") == normalized:
            return option
    alias = CHOICE_ALIASES.get(step_id, {}).get(choice.lower())
    if alias and alias in options:
        return alias
    raise ValueError(f"unknown choice `{raw_choice}` for step `{step_id}`")


@dataclass
class ForgeSession:
    session_id: str
    intent: str
    source_path: str | None
    crystallized_intent: dict[str, object]
    contract_shape: dict[str, object]
    package_preview: dict[str, object]
    steps: list[dict[str, object]]
    cursor: int
    answers: dict[str, dict[str, str]] = field(default_factory=dict)

    def current_step(self) -> dict[str, object]:
        step = self.steps[self.cursor] if self.cursor < len(self.steps) else None
        if step is None:
            return {
                "status": "ready_for_generation",
                "observation": "All Forge calibration steps have been satisfied for this first-pass session.",
                "recommendation": "Review the contract shape, then generate the package for manual hardening.",
                "contract_shape": self.contract_shape,
            }
        return {
            "status": "in_progress",
            "step_id": step["step_id"],
            "index": self.cursor + 1,
            "total_steps": len(self.steps),
            "observation": step["observation"],
            "recommendation": step["recommendation"],
            "options": step.get("options", []),
            "option_items": build_step_options(step["step_id"], list(step.get("options", []))),
            "known_answers": self.answers,
            "contract_shape": self.contract_shape,
        }

    def is_complete(self) -> bool:
        return self.cursor >= len(self.steps)

    def commit(self, choice: str, reason: str) -> dict[str, object]:
        if self.is_complete():
            return {"ok": False, "status": "already_complete"}
        step = self.steps[self.cursor]
        self.answers[step["step_id"]] = {"choice": choice, "reason": reason}
        self._apply_choice(step["step_id"], choice, reason)
        self._rebuild_package_preview()
        self.cursor += 1
        return {"ok": True, "status": "committed", "next_step": self.current_step()}

    def _apply_choice(self, step_id: str, choice: str, reason: str) -> None:
        if step_id == "problem_framing":
            self.crystallized_intent["problem_framing"] = choice
        elif step_id == "outcome":
            self.crystallized_intent["outcome"] = choice
            if choice == "artifact_creation":
                self.contract_shape["terminal_outcomes"] = ["GENERATED", "FAILED"]
                self.contract_shape["verification_codes"] = ["ARTIFACT_READY", "ARTIFACT_FAILED"]
            elif choice == "state_change":
                self.contract_shape["terminal_outcomes"] = ["APPLIED", "BLOCKED", "FAILED"]
                self.contract_shape["verification_codes"] = ["STATE_APPLIED", "HOLD_REQUIRED", "STATE_FAILED"]
            elif choice == "decision_preparation":
                self.contract_shape["terminal_outcomes"] = ["PREPARED", "NEEDS_REVIEW", "FAILED"]
                self.contract_shape["verification_codes"] = ["DECISION_READY", "REVIEW_REQUIRED", "PREPARATION_FAILED"]
        elif step_id == "reality":
            self.crystallized_intent["inputs_reality"]["selected_mode"] = choice
            if choice == "goal_plus_evidence":
                if "evidence_ref" not in self.contract_shape["optional_inputs"]:
                    self.contract_shape["optional_inputs"].append("evidence_ref")
            elif choice == "goal_plus_constraints":
                if "constraint_context" not in self.contract_shape["optional_inputs"]:
                    self.contract_shape["optional_inputs"].append("constraint_context")
        elif step_id == "strategy":
            self.crystallized_intent["strategy"] = choice
            if choice == "rigid_plan":
                self.contract_shape["source_execution_mode"] = "deterministic"
                self.contract_shape["engine15_execution_mode"] = "SAFE_INTERNAL"
            elif choice == "adaptive_feedback":
                self.contract_shape["source_execution_mode"] = "ai_assisted"
                self.contract_shape["engine15_execution_mode"] = "DRAFT_REVIEW"
            elif choice == "outcome_backwards":
                if "goal_state" not in self.contract_shape["required_inputs"]:
                    self.contract_shape["required_inputs"].append("goal_state")
        elif step_id == "verification":
            self.crystallized_intent["verification"] = choice
            if choice == "artifact_exists":
                self.contract_shape["verification_codes"] = ["ARTIFACT_READY", "ARTIFACT_MISSING"]
            elif choice == "behavior_changed":
                self.contract_shape["verification_codes"] = ["BEHAVIOR_CHANGED", "CHANGE_NOT_CONFIRMED"]
            elif choice == "external_review":
                self.contract_shape["verification_codes"] = ["REVIEW_ACCEPTED", "REVIEW_REJECTED"]
            elif choice == "combined_verification":
                self.contract_shape["verification_codes"] = ["AUTO_CHECK_PASSED", "HUMAN_REVIEW_REQUIRED", "CHECK_FAILED"]
        elif step_id == "constraints":
            self.crystallized_intent["constraints"] = [choice]
            if choice == "legal_boundary":
                self.contract_shape["engine15_execution_mode"] = "DRAFT_REVIEW"
            elif choice == "scope_boundary":
                self.contract_shape["service_bindings"] = self.contract_shape["service_bindings"][:2]
        elif step_id == "decision_rights":
            self.crystallized_intent["decision_rights"]["selected_mode"] = choice
            if choice == "human_approves_final_only":
                self.contract_shape["source_execution_mode"] = "human_gated"
                if "connector.human.review" not in self.contract_shape["service_bindings"]:
                    self.contract_shape["service_bindings"].append("connector.human.review")
            elif choice == "system_local_autonomy_with_guardrails":
                self.contract_shape["engine15_execution_mode"] = "LIVE_READ_ONLY"
        elif step_id == "uncertainty":
            self.crystallized_intent["uncertainty"] = [choice]
            if choice == "input_incompleteness" and "input_quality_note" not in self.contract_shape["optional_inputs"]:
                self.contract_shape["optional_inputs"].append("input_quality_note")
        elif step_id == "commitment":
            self.crystallized_intent["commitment"] = reason
            if choice == "keep_private":
                self.package_preview["source_contract_package_v0.json"]["visibility"] = "private"
            elif choice == "publish_public_later":
                self.package_preview["source_contract_package_v0.json"]["visibility"] = "public"

    def _rebuild_package_preview(self) -> None:
        title = str(self.contract_shape["title"])
        summary = str(self.package_preview["source_contract_package_v0.json"]["summary"])
        required_inputs = list(dict.fromkeys(self.contract_shape["required_inputs"]))
        optional_inputs = list(dict.fromkeys(self.contract_shape["optional_inputs"]))
        service_bindings = list(dict.fromkeys(self.contract_shape["service_bindings"]))
        terminal_outcomes = list(dict.fromkeys(self.contract_shape["terminal_outcomes"]))
        verification_codes = list(dict.fromkeys(self.contract_shape["verification_codes"]))

        source_contract = self.package_preview["source_contract_package_v0.json"]
        source_contract["contract_class"] = self.contract_shape["contract_class"]
        source_contract["execution_mode"] = self.contract_shape["source_execution_mode"]
        source_contract["required_inputs"] = required_inputs
        source_contract["optional_inputs"] = optional_inputs
        source_contract["service_bindings"] = service_bindings

        runtime_manifest = self.package_preview["runtime_manifest_v0.json"]
        runtime_manifest["execution_mode"] = self.contract_shape["engine15_execution_mode"]
        runtime_manifest["terminal_outcomes"] = terminal_outcomes
        runtime_manifest["capabilities"] = {
            "self_contained": False,
            "external_state": len(service_bindings) > 0,
            "mutation": False,
            "human_gated": self.contract_shape["source_execution_mode"] == "human_gated",
            "safe_internal_only": self.contract_shape["engine15_execution_mode"] == "SAFE_INTERNAL",
            "live_read_only": self.contract_shape["engine15_execution_mode"] == "LIVE_READ_ONLY",
        }

        policy_calibration = self.package_preview["policy_calibration_v0.json"]
        policy_calibration["source_execution_mode"] = self.contract_shape["source_execution_mode"]
        policy_calibration["engine15_execution_mode"] = self.contract_shape["engine15_execution_mode"]
        policy_calibration["mapping"] = {
            code: terminal_outcomes[min(index, len(terminal_outcomes) - 1)]
            for index, code in enumerate(verification_codes)
        }

        self.package_preview["input_model_v0.json"] = _build_input_model(required_inputs)
        self.package_preview["verification_model_v0.json"] = _build_verification_model(
            verification_codes,
            terminal_outcomes,
        )
        self.package_preview["README.md"] = _render_readme(title, summary, required_inputs, service_bindings)
        self.package_preview["execution_note.md"] = _render_execution_note_with_context(
            title,
            self.contract_shape["source_execution_mode"],
            service_bindings,
            list(self.crystallized_intent.get("constraints", [])),
            list(self.crystallized_intent.get("uncertainty", [])),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "session_id": self.session_id,
            "intent": self.intent,
            "source_path": self.source_path,
            "crystallized_intent": self.crystallized_intent,
            "contract_shape": self.contract_shape,
            "package_preview": self.package_preview,
            "steps": self.steps,
            "cursor": self.cursor,
            "answers": self.answers,
        }

    def save(self, session_dir: Path = FORGE_SESSION_DIR) -> Path:
        session_dir.mkdir(parents=True, exist_ok=True)
        path = session_dir / f"{self.session_id}.json"
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return path

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

        return {
            "ok": True,
            "status": "generated",
            "output_path": str(root),
            "contract_id": self.contract_shape["contract_id"],
            "files": sorted(files.keys()),
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
    process_ref = f"pkg_{_slugify(title)}_v1_draft"
    executor_ref = f"runtime_executor.{_slugify(title)}_v1"
    required_inputs = list(seeded_contract.get("required_inputs") or shaping["required_inputs"])
    optional_inputs = list(seeded_contract.get("optional_inputs") or shaping["optional_inputs"])
    service_bindings = list(seeded_contract.get("service_bindings") or shaping["service_bindings"])
    summary = str(
        seeded_contract.get("summary")
        or f"Contract generated from the business intent: {raw_intent.strip()}."
    )
    timestamp = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    crystallized_intent = {
        "intent": raw_intent,
        "problem_framing": "result_definition",
        "outcome": "Create a bounded contract package that can later be registered in MOVA.",
        "inputs_reality": {
            "facts": [],
            "assumptions": ["This first Forge slice uses template-driven defaults that require manual review."],
        },
        "strategy": "contract_first_authoring",
        "constraints": ["Use canonical contract_package_v0 structure."],
        "decision_rights": {
            "human_controls": ["final contract review", "publication choice", "connector binding"],
            "system_may": ["prepare a first-pass package draft"],
        },
        "verification": "Package validates structurally and is understandable by the author.",
        "uncertainty": ["Connector bindings and execution posture may need refinement before production publication."],
        "commitment": "The user owns the contract package and decides whether it remains private or is later published.",
        "status": "crystallization_complete",
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
            "status": "draft",
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
            "status": "DRAFT",
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
                "First-pass Forge package defaults to review-first posture until the author hardens policy and runtime wiring."
            ],
        }
    )

    steps = [
        {
            "step_id": step_id,
            "observation": description,
            "recommendation": f"Confirm or refine `{step_id}` before final package generation.",
            "options": STEP_OPTIONS.get(step_id, []),
        }
        for step_id, description in STEP_DEFINITIONS
    ]

    package_preview = {
        "README.md": _render_readme(title, summary, required_inputs, service_bindings),
        "execution_note.md": _render_execution_note(title, contract_shape["source_execution_mode"], service_bindings),
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
        steps=steps,
        cursor=0,
    )


def load_forge_session(session_id: str, session_dir: Path = FORGE_SESSION_DIR) -> ForgeSession:
    path = session_dir / f"{session_id}.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_steps = list(payload["steps"])
    normalized_steps = []
    for step in raw_steps:
        step_id = str(step["step_id"])
        normalized = dict(step)
        normalized.setdefault("options", STEP_OPTIONS.get(step_id, []))
        normalized_steps.append(normalized)
    return ForgeSession(
        session_id=str(payload["session_id"]),
        intent=str(payload["intent"]),
        source_path=payload.get("source_path"),
        crystallized_intent=dict(payload["crystallized_intent"]),
        contract_shape=dict(payload["contract_shape"]),
        package_preview=dict(payload["package_preview"]),
        steps=normalized_steps,
        cursor=int(payload["cursor"]),
        answers=dict(payload.get("answers", {})),
    )


def list_forge_sessions(session_dir: Path = FORGE_SESSION_DIR) -> list[dict[str, object]]:
    if not session_dir.exists():
        return []
    items: list[dict[str, object]] = []
    for path in sorted(session_dir.glob("forge_*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        items.append(
            {
                "session_id": payload.get("session_id"),
                "intent": payload.get("intent"),
                "cursor": payload.get("cursor"),
                "total_steps": len(payload.get("steps", [])),
                "is_complete": int(payload.get("cursor", 0)) >= len(payload.get("steps", [])),
                "path": str(path),
            }
        )
    return items
