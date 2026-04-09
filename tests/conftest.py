from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture
def example_contract_package(tmp_path: Path) -> Path:
    root = tmp_path / "invoice_processing_v0"
    models = root / "models"
    models.mkdir(parents=True)
    fixtures = root / "fixtures"
    fixtures.mkdir()

    (root / "manifest.json").write_text(
        json.dumps(
            {
                "schema_id": "package.contract_package_manifest_v0",
                "package_id": "contract.demo.invoice_processing.v0",
                "version": "1.0.0",
                "start_step_id": "extract_invoice",
                "terminal_statuses": ["completed", "human_review_required"],
                "files": {},
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (root / "flow.json").write_text(
        json.dumps(
            {
                "flow_id": "contract.demo.invoice_processing.v0",
                "start_step_id": "extract_invoice",
                "terminal_statuses": ["completed", "human_review_required"],
                "steps": [
                    {
                        "step_id": "extract_invoice",
                        "step_classification": "safe_internal",
                    }
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (root / "classification_policy.json").write_text(
        json.dumps(
            {
                "policy_id": "mova.step_classification_policy_v0",
                "version": "0.1.0",
                "allowed_execution_modes": ["SAFE_INTERNAL"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (root / "classification_results.json").write_text(
        json.dumps(
            [
                {
                    "step_id": "extract_invoice",
                    "execution_mode": "SAFE_INTERNAL",
                }
            ],
            indent=2,
        ),
        encoding="utf-8",
    )
    (root / "runtime_binding_set.json").write_text(
        json.dumps(
            {
                "bindings": [
                    {
                        "binding_id": "binding.invoice.extract.v0",
                        "step_id": "extract_invoice",
                        "binding_ref": "runtime://invoice/extract",
                        "execution_mode": "SAFE_INTERNAL",
                        "notes": [
                            "derived_from_executor:native.invoice",
                            "derived_from_engine_mode:SAFE_INTERNAL",
                        ],
                    }
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (models / "input_model_v0.json").write_text(
        json.dumps(
            {
                "schema_id": "model.input_model_v0",
                "fields": [{"name": "file_url", "type": "string", "required": True}],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (models / "verification_model_v0.json").write_text(
        json.dumps(
            {
                "schema_id": "model.verification_model_v0",
                "verification_codes": [{"code": "verify.invoice.basic"}],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (root / "README.md").write_text("# Demo package\n", encoding="utf-8")

    return root
