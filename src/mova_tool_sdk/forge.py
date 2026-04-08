from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from .contracts import package_root


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


def _render_readme(title: str, summary: str, required_inputs: list[str], binding_ref: str, terminal_statuses: list[str]) -> str:
    return (
        f"# {title}\n\n"
        f"{summary}\n\n"
        "## Status\n\n"
        "- This is a candidate canonical MOVA contract package.\n"
        "- It is intended for authoring/lab handoff before freeze.\n\n"
        "## Required Inputs\n\n"
        + "\n".join(f"- `{name}`" for name in required_inputs)
        + "\n\n## Runtime Binding\n\n"
        f"- `{binding_ref}`\n\n"
        "## Terminal Statuses\n\n"
        + "\n".join(f"- `{status}`" for status in terminal_statuses)
        + "\n"
    )


def _render_execution_note(title: str, engine_mode: str, unresolved_gaps: list[str]) -> str:
    lines = [
        f"# Execution Note — {title}",
        "",
        f"- Engine execution mode: `{engine_mode}`",
        "- This package is a candidate and must be proven through authoring/lab before freeze.",
    ]
    if unresolved_gaps:
        lines.append("- Open gaps:")
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
    return {
        "verification_codes": [
            {
                "code": code,
                "maps_to": terminal_outcomes[min(index, len(terminal_outcomes) - 1)],
                "severity": "info" if index == 0 else "warning",
            }
            for index, code in enumerate(verification_codes)
        ]
    }


def _classification_policy() -> dict[str, object]:
    return {
        "schema_id": "ds.step_classification_policy_v0",
        "policy_id": "mova.step_classification_policy_v0",
        "version": "0.1.0",
        "scope": "contract_authoring",
        "purpose": "classify each contract step before runtime",
        "allowed_execution_modes": ["DETERMINISTIC", "AI_ATOMIC", "EXTERNAL_CALL", "HUMAN_GATE"],
        "core_invariant": "Every step must be classified before execution. Runtime executes the chosen mode and does not choose the nature of the step.",
    }


def _classify_intent(intent: str) -> dict[str, object]:
    text = intent.lower()
    contract_class = "custom"
    required_inputs = ["subject_id"]
    execution_mode = "DETERMINISTIC"
    engine_execution_mode = "SAFE_INTERNAL"
    binding_kind = "deterministic_handler"
    binding_ref = "custom_contract_v0"
    terminal_statuses = ["COMPLETED", "FAILED"]
    verification_codes = ["SUCCESS", "FAILED"]
    unresolved_gaps = [
        "Authoring and lab evidence are still required before freeze.",
        "Connector and policy wiring must be proven in platform context.",
    ]

    if "invoice" in text or "iban" in text or "vendor" in text:
        contract_class = "finance"
        required_inputs = ["file_url"]
        execution_mode = "EXTERNAL_CALL"
        engine_execution_mode = "DRAFT_REVIEW"
        binding_kind = "mcp_tool_call"
        binding_ref = "invoice_processing_v0"
        terminal_statuses = ["APPROVED", "REVIEW_REQUIRED", "REJECTED", "BLOCKED"]
        verification_codes = ["INVOICE_EXTRACTED", "IBAN_VERIFIED", "REVIEW_REQUIRED"]
    elif "ticket" in text or "helpdesk" in text or "support" in text:
        contract_class = "ticket"
        required_inputs = ["title", "summary"]
        execution_mode = "EXTERNAL_CALL"
        engine_execution_mode = "DRAFT_REVIEW"
        binding_kind = "ticket_router_call"
        binding_ref = "ticket_triage_v0"
        terminal_statuses = ["TRIAGED", "ESCALATED", "BLOCKED"]
        verification_codes = ["ROUTE_MATCH", "ESCALATION_REQUIRED", "INSUFFICIENT_DATA"]
    elif "crm" in text or "lead" in text or "sales" in text:
        contract_class = "crm"
        required_inputs = ["subject_id"]
        execution_mode = "EXTERNAL_CALL"
        engine_execution_mode = "DRAFT_REVIEW"
        binding_kind = "mcp_tool_call"
        binding_ref = "crm_sync_v0"
        terminal_statuses = ["UPDATED", "QUEUED", "FAILED"]
        verification_codes = ["CRM_UPDATED", "SYNC_DEFERRED", "SYNC_FAILED"]

    return {
        "contract_class": contract_class,
        "required_inputs": required_inputs,
        "execution_mode": execution_mode,
        "engine_execution_mode": engine_execution_mode,
        "binding_kind": binding_kind,
        "binding_ref": binding_ref,
        "terminal_statuses": terminal_statuses,
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
        manifest = self.package_preview["manifest.json"]
        binding_set = self.package_preview["runtime_binding_set.json"]
        binding = binding_set["bindings"][0]
        return {
            "session_id": self.session_id,
            "intent": self.intent,
            "contract_id": self.contract_shape["contract_id"],
            "contract_class": self.contract_shape["contract_class"],
            "execution_mode": binding["execution_mode"],
            "engine_execution_mode": self.contract_shape["engine_execution_mode"],
            "required_inputs": list(self.contract_shape["required_inputs"]),
            "binding_ref": binding["binding_ref"],
            "package_version": manifest["version"],
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
            "env_type": "sdk_local_candidate_handoff_v2",
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
                "canonical_package": {
                    "manifest": self.package_preview["manifest.json"],
                    "flow": self.package_preview["flow.json"],
                    "classification_policy": self.package_preview["classification_policy.json"],
                    "classification_results": self.package_preview["classification_results.json"],
                    "runtime_binding_set": self.package_preview["runtime_binding_set.json"],
                    "input_model_v0": self.package_preview["models/input_model_v0.json"],
                    "verification_model_v0": self.package_preview["models/verification_model_v0.json"],
                    "readme": self.package_preview["README.md"],
                }
            },
            "handoff": {
                "target": target,
                "intent": "create_candidate_draft" if target == "authoring" else "test_candidate_in_lab",
            },
        }

    def generate_package(self, output_path: str | Path) -> dict[str, object]:
        root = Path(output_path).expanduser().resolve()
        (root / "models").mkdir(parents=True, exist_ok=True)
        (root / "fixtures").mkdir(exist_ok=True)

        files = {
            "README.md": self.package_preview["README.md"],
            "execution_note.md": self.package_preview["execution_note.md"],
            "manifest.json": json.dumps(self.package_preview["manifest.json"], ensure_ascii=False, indent=2),
            "flow.json": json.dumps(self.package_preview["flow.json"], ensure_ascii=False, indent=2),
            "classification_policy.json": json.dumps(self.package_preview["classification_policy.json"], ensure_ascii=False, indent=2),
            "classification_results.json": json.dumps(self.package_preview["classification_results.json"], ensure_ascii=False, indent=2),
            "runtime_binding_set.json": json.dumps(self.package_preview["runtime_binding_set.json"], ensure_ascii=False, indent=2),
            "models/input_model_v0.json": json.dumps(self.package_preview["models/input_model_v0.json"], ensure_ascii=False, indent=2),
            "models/verification_model_v0.json": json.dumps(self.package_preview["models/verification_model_v0.json"], ensure_ascii=False, indent=2),
            "fixtures/README.md": "Place candidate package fixtures here for lab validation.\n",
        }

        for relative_path, contents in files.items():
            target = root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(contents, encoding="utf-8")

        handoff_payload = self.to_local_candidate_handoff()
        (root / "sdk_local_candidate_handoff_v2.json").write_text(
            json.dumps(handoff_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return {
            "ok": True,
            "status": "generated",
            "output_path": str(root),
            "contract_id": self.contract_shape["contract_id"],
            "files": sorted([*files.keys(), "sdk_local_candidate_handoff_v2.json"]),
        }


def start_forge(intent: str | None = None, source_path: str | None = None) -> ForgeSession:
    seeded_contract: dict[str, object] = {}
    if source_path:
        root = package_root(source_path)
        manifest_file = root / "manifest.json"
        if manifest_file.exists():
            seeded_contract = json.loads(manifest_file.read_text(encoding="utf-8"))

    raw_intent = intent or str(seeded_contract.get("summary") or seeded_contract.get("title") or "custom contract")
    shaping = _classify_intent(raw_intent)
    title = _title_from_intent(raw_intent)
    slug = f"contract.{_slugify(title)}.v1"
    summary = f"Candidate contract generated from the business intent: {raw_intent.strip()}."
    timestamp = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    required_inputs = list(shaping["required_inputs"])
    terminal_statuses = list(shaping["terminal_statuses"])
    verification_codes = list(shaping["verification_codes"])
    binding_ref = str(shaping["binding_ref"])
    execution_mode = str(shaping["execution_mode"])
    engine_execution_mode = str(shaping["engine_execution_mode"])

    crystallized_intent = {
        "status": "candidate_ready",
        "raw_intent": raw_intent,
        "intent_context": {
            "goal_description": "Turn the calibrated business task into a canonical candidate contract package for platform testing.",
            "verification_criteria": [
                "The package validates structurally.",
                "The package is suitable for authoring/lab handoff.",
            ],
            "invariants": ["Use frozen MOVA contract package canon."],
        },
        "unresolved_gaps": list(shaping["unresolved_gaps"]),
        "recommendation": "Hand this canonical candidate into MOVA authoring/lab flow for test runs and hardening.",
    }

    contract_shape = {
        "title": title,
        "contract_id": slug,
        "contract_class": str(shaping["contract_class"]),
        "required_inputs": required_inputs,
        "execution_mode": execution_mode,
        "engine_execution_mode": engine_execution_mode,
        "binding_ref": binding_ref,
    }

    manifest = {
        "schema_id": "package.contract_package_manifest_v0",
        "package_id": slug,
        "version": "1.0.0",
        "flow_ref": "flow.json",
        "classification_policy_ref": "classification_policy.json",
        "classification_result_set_ref": "classification_results.json",
        "classification_result_refs": ["classification://execute_contract"],
        "runtime_binding_set_ref": "runtime_binding_set.json",
        "model_refs": ["models/input_model_v0.json", "models/verification_model_v0.json"],
        "package_invariants": [
            "every_contract_step_must_have_classification",
            "every_executable_step_must_have_runtime_binding",
            "binding_execution_mode_must_match_step_classification",
            "ai_atomic_cannot_make_final_business_decisions",
            "external_call_must_not_hide_decision_logic",
            "package_binds_ds_and_env_without_changing_ds_semantics",
        ],
    }
    flow = {
        "schema_id": "ds.contract_flow_v0",
        "flow_id": slug,
        "flow_intent": summary,
        "input_model_ref": "models/input_model_v0.json",
        "start_step_id": "execute_contract",
        "steps": [
            {
                "schema_id": "ds.contract_step_v0",
                "step_id": "execute_contract",
                "step_intent": summary,
                "classification_ref": "classification://execute_contract",
                "runtime_binding_ref": "binding://execute_contract",
                "input_model_ref": "models/input_model_v0.json",
                "output_model_ref": "models/verification_model_v0.json",
                "terminal_behavior": {"is_terminal": True},
            }
        ],
        "terminal_statuses": terminal_statuses,
        "flow_invariants": [
            "all_steps_must_be_classified_before_runtime",
            "runtime_binding_must_match_step_classification",
            "package_binds_ds_and_env_without_changing_ds_semantics",
        ],
    }
    classification_results = [
        {
            "schema_id": "ds.step_classification_result_v0",
            "step_id": "execute_contract",
            "step_intent": summary,
            "policy_ref": "mova.step_classification_policy_v0",
            "question_answers": {
                "Q1": execution_mode == "DETERMINISTIC",
                "Q2": False,
                "Q3": execution_mode == "EXTERNAL_CALL",
                "Q4": False,
                "Q5": execution_mode == "DETERMINISTIC",
            },
            "execution_mode": execution_mode,
            "why_this_mode": [
                "This is the narrowest executable candidate shape for the declared business task."
            ],
            "why_not_other_modes": {
                "AI_ATOMIC": ["AI_ATOMIC must not hide final business decisions."],
                "HUMAN_GATE": ["Human review remains a downstream platform choice, not the root package shape."],
            },
            "expected_output_shape": {
                "verification_code": "string",
                "terminal_outcome": "|".join(terminal_statuses),
            },
        }
    ]
    runtime_binding_set = {
        "schema_id": "env.runtime_binding_set_v0",
        "binding_set_id": f"runtime_bindings.{slug}.v0",
        "flow_ref": slug,
        "environment_id": "default",
        "tenant_scope": "shared",
        "bindings": [
            {
                "schema_id": "env.runtime_execution_binding_v0",
                "binding_id": "binding://execute_contract",
                "step_id": "execute_contract",
                "execution_mode": execution_mode,
                "binding_kind": "deterministic_handler" if execution_mode == "DETERMINISTIC" else "mcp_tool_call",
                "binding_ref": binding_ref,
                "input_adapter_ref": f"adapter.input.{slug}.v0",
                "output_adapter_ref": f"adapter.output.{slug}.v0",
                "retry_policy_ref": "policy.retry.none_v0" if execution_mode == "DETERMINISTIC" else "policy.retry.external_call_default_v0",
                "timeout_policy_ref": "policy.timeout.local_fast_v0" if execution_mode == "DETERMINISTIC" else "policy.timeout.external_call_default_v0",
                "notes": [
                    f"derived_from_executor:{binding_ref}_executor_v0",
                    f"derived_from_engine_mode:{engine_execution_mode}",
                ],
            }
        ],
        "set_invariants": [
            "every_executable_step_must_have_one_binding",
            "binding_execution_mode_must_match_step_classification",
            "no_binding_may_override_contract_semantics",
        ],
    }

    package_preview = {
        "README.md": _render_readme(title, summary, required_inputs, binding_ref, terminal_statuses),
        "execution_note.md": _render_execution_note(title, engine_execution_mode, list(shaping["unresolved_gaps"])),
        "manifest.json": manifest,
        "flow.json": flow,
        "classification_policy.json": _classification_policy(),
        "classification_results.json": classification_results,
        "runtime_binding_set.json": runtime_binding_set,
        "models/input_model_v0.json": _build_input_model(required_inputs),
        "models/verification_model_v0.json": _build_verification_model(verification_codes, terminal_statuses),
    }

    return ForgeSession(
        session_id=f"forge_{uuid4().hex}",
        intent=raw_intent,
        source_path=source_path,
        crystallized_intent=crystallized_intent,
        contract_shape=contract_shape,
        package_preview=package_preview,
    )
