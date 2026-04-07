# mova-tool-sdk

Python-first MOVA SDK scaffold.

`mova-tool-sdk` is the new SDK layer above the MOVA platform:

- CLI for humans
- Python API for programmatic integration
- future MCP/native tool mode for agents

This repo is intentionally separate from the legacy `mova_sdk` and from `mova-bridge`.

## Current scope

Version `0.1.0` starts with the shared base:

- config loading and persistence
- auth key management
- local contract-package validation
- local contract-package inspection
- HTTP client scaffold for future platform calls
- CLI command groups matching the new SDK spec

## Current command groups

- `mova register`
- `mova auth set-key`
- `mova auth check`
- `mova auth whoami`
- `mova publish`
- `mova forge`
- `mova validate`
- `mova inspect`
- `mova execute`
- `mova status`
- `mova runs list`
- `mova decisions pending`
- `mova decide`
- `mova audit`
- `mova connectors list`
- `mova connectors add`
- `mova connectors remove`
- `mova connectors test`
- `mova connectors registered`
- `mova contracts list`
- `mova contracts pull`
- `mova usage`
- `mova plan`
- `mova cost`
- `mova serve --mode mcp`

## Contract package canon

The SDK currently validates the following package files:

- `source_contract_package_v0.json`
- `runtime_manifest_v0.json`
- `policy_calibration_v0.json`
- `input_model_v0.json`
- `verification_model_v0.json`
- `README.md`
- `execution_note.md`

## Status

This is the new canonical SDK scaffold.
The first remote slice is already wired against the current platform through a temporary bridge-compatible adapter inside the client:

- `mova execute` registers a local contract package and starts a run
- `mova status` reads run state
- `mova audit` exports the run audit bundle
- `mova decide` maps to operator approve/deny actions

Canonical config/env language now follows the SDK spec:

- `MOVA_API_KEY`
- `MOVA_PLATFORM_URL`

Local/dev compatibility aliases are still accepted:

- `MOVA_BASE_URL`
- `MOVA_RUNTIME_EXECUTE_TOKEN`
- `MOVA_ADMIN_READ_TOKEN`
- `MOVA_OPERATOR_RECOVERY_TOKEN`

## Public Python API direction

The repo now exposes the spec-shaped Python entrypoints:

```python
from mova_tool_sdk import Forge, Mova

m = Mova()
result = m.execute(contract_id="finance.invoice_ocr_v1", input_data={"file_url": "https://..."})

forge = Forge()
session = forge.start(intent="automate invoice processing")
```

`Mova` is the canonical public API shape. Internally it still adapts to the current route surface while the platform SDK endpoints are being finalized.

## First Forge slice

`Forge` is no longer a placeholder. The current first slice supports:

- turning an `intent` into a first-pass crystallized contract shape
- generating a canonical `contract_package_v0` to disk
- seeding the flow from an existing package directory with `--from`

Example:

```bash
mova forge --intent "automate invoice processing with human approval" --output ./my-contract
```

Forge sessions can now be resumed locally:

```bash
mova forge --intent "automate invoice processing with human approval"
mova forge sessions
mova forge resume <session_id>
mova forge commit <session_id> result-definition --reason "Need a bounded finance review contract"
```

This first slice is intentionally review-first:

- generated packages default to `DRAFT_REVIEW`
- connector bindings are placeholders until the author hardens them
- publication and execution remain separate downstream steps
