# mova-tool-sdk

Python-first MOVA SDK scaffold.

`mova-tool-sdk` is the thin Python SDK layer above the MOVA platform:

- local soft-entry CLI
- Python API for programmatic integration
- client access to the existing `mcp_door` / state-machine surface

This repo is intentionally separate from the legacy `mova_sdk` and from `mova-bridge`.

Current release state:

- package build is working
- test suite is intended to run from a clean checkout without manual `PYTHONPATH` setup
- the SDK is suitable for an early public beta with intentionally narrow scope

Release docs:

- [Release Notes 0.1.0 Beta](./RELEASE_NOTES_0.1.0-beta.md)
- [Public Getting Started](./docs/PUBLIC_GETTING_STARTED.md)

## Current scope

Version `0.1.0` starts with the shared base:

- config loading and persistence
- auth key management
- local candidate-package validation
- local candidate-package inspection
- local `Forge` candidate generation
- thin client calls into the current platform surface

## Current runtime boundary

The SDK now follows the real `mcp_door` contour instead of the earlier temporary bridge routes.

Current live client targets are:

- `POST /v1/register`
- `GET /v1/me`
- `POST /v1/api-keys`
- `POST /v0/registry/contracts`
- `GET /v0/registry/contracts/:contract_id`
- `POST /intake/runs`
- `GET /intake/runs/:run_id`
- `GET /intake/runs/:run_id/artifacts`
- `GET /intake/runs/:run_id/admission-result`
- `GET /intake/runs/:run_id/dispatch-result`
- `GET /intake/runs/:run_id/execute-dry-result`
- `GET /intake/runs/:run_id/execute-internal-result`
- `GET /intake/runs/:run_id/continuation-result`
- `GET /intake/runs/:run_id/runtime-eligibility`
- `GET /intake/runs/:run_id/access-grant`
- `GET /artifacts/:artifact_id`
- `POST /operator/runs/:run_id/approve`
- `POST /operator/runs/:run_id/deny`
- `GET /v0/admin/audit/runs/:run_id/export`

Current limitation:

- generic execution by platform `contract_id` is not exposed yet
- the SDK can honestly execute from a local contract package path because it can derive a runtime descriptor from the canonical package files
- contract-id-first execution should only be added after `mcp_door` exposes a real runtime resolution route for it

## Current command groups

- `mova auth set-key`
- `mova auth register`
- `mova auth me`
- `mova auth issue-key`
- `mova auth check`
- `mova auth whoami`
- `mova forge`
- `mova validate`
- `mova inspect`
- `mova execute`
- `mova handoff`
- `mova forms list|get`
- `mova authoring get|answer|gap-analysis|cancel`
- `mova draft`
- `mova lab`
- `mova lab-status`
- `mova evidence list|get|history|lineage|archive`
- `mova promote`
- `mova contracts list|get|history|lineage|publish|deprecate|retire|reactivate`
- `mova connectors list|get|add`
- `mova bindings list|get|history|lineage|create|attach|rebind|activate|enable-steady-state|pause|disable`
- `mova status --view summary|artifacts|admission|dispatch|dry|internal|continuation|eligibility|access-grant`
- `mova artifact get`
- `mova decide`
- `mova audit`

## Contract package canon

The SDK currently validates the following package files:

- `manifest.json`
- `flow.json`
- `classification_policy.json`
- `classification_results.json`
- `runtime_binding_set.json`
- `models/input_model_v0.json`
- `models/verification_model_v0.json`
- `README.md`

## Status

This is the new canonical soft-entry SDK scaffold.
The current role of the SDK is intentionally narrow:

- local AI-guided calibration will eventually end at a candidate contract package
- the platform lifecycle after that remains inside `mova-state-1.5`
- the SDK should connect to existing platform endpoints instead of inventing a second authoring/runtime layer

Canonical config/env language now follows the SDK spec:

- `MOVA_API_KEY`
- `MOVA_PLATFORM_URL`

See [.env.example](/d:/Projects_MOVA/mova-tool-sdk/.env.example) for a minimal local bootstrap shape.

Local/dev compatibility aliases are still accepted:

- `MOVA_BASE_URL`
- `MOVA_RUNTIME_EXECUTE_TOKEN`
- `MOVA_ADMIN_READ_TOKEN`
- `MOVA_OPERATOR_RECOVERY_TOKEN`

## Public Identity Beta

The deployed public beta identity surface is now part of the SDK:

- `mova auth register <email>`
- `mova auth me`
- `mova auth issue-key`

Useful shortcuts:

- `mova auth register <email> --set-key`
  Stores the returned personal API key into local SDK config.
- `mova auth issue-key --scopes self_read,runs_write --set-key`
  Mints a narrower personal API key and makes it the active local key.

## Public Python API direction

The repo now exposes the spec-shaped Python entrypoints:

```python
from mova_tool_sdk import Forge, Mova

m = Mova()
result = m.execute(
    contract_path="./my-contract",
    tenant_id="tenant_demo_shop_v0",
    input_data={"file_url": "https://..."},
)

forge = Forge()
session = forge.start(intent="automate invoice processing")
```

`Mova` is the canonical public API shape. The client is transitional and must progressively align to existing `mcp_door` endpoints rather than define new lifecycle layers from outside.

## Forge Boundary

`Forge` stays local and light. Its purpose is:

- turn a business intent into a canonical candidate package
- emit a platform-facing `sdk_local_candidate_handoff_v2` envelope
- hand the candidate off into the real platform contour for authoring draft, lab testing, and promotion

Example:

```bash
mova forge --intent "automate invoice processing with human approval" --output ./my-contract
```

Current expected flow:

1. `mova forge ...`
2. receive candidate package locally
3. hand off candidate into platform flow via `sdk_local_candidate_handoff_v2.json`
4. the SDK seeds the authoring session with:
   - `resolved_fields`
   - `seed_canonical_package`
5. platform performs authoring draft / lab / promotion

Minimal platform continuation commands now map to existing routes:

- `mova forms list|get` -> `GET /v0/authoring/forms*`
- `mova handoff` -> `POST /v0/authoring/sessions`
- `mova authoring get|answer|gap-analysis|cancel` -> `GET|POST /v0/authoring/sessions/*`
- `mova draft` -> `POST /v0/authoring/sessions/:session_id/emit-draft`
- `mova lab` -> `POST /v0/lab/runs`
- `mova lab-status` -> `GET /v0/lab/runs/:lab_run_id`
- `mova evidence list|get|history|lineage|archive` -> `GET|POST /v0/lab/evidence/*`
- `mova promote` -> `POST /v0/lab/promote`
- `mova contracts list|get|history|lineage|publish|deprecate|retire|reactivate` -> `GET|POST /v0/registry/contracts/*`
- `mova connectors list|get|add` -> `GET|POST /v0/business/connectors*`
- `mova bindings list|get|history|lineage|create|attach|rebind|activate|enable-steady-state|pause|disable` -> `GET|POST /v0/business/bindings*`
- `mova status --view ...` -> `GET /intake/runs/:run_id*`
- `mova artifact get` -> `GET /artifacts/:artifact_id`

`mova handoff` can now use either:

- `--intent "..."` for a raw direct handoff
- `--candidate-file ./sdk_local_candidate_handoff_v2.json` for the canonical SDK-generated handoff envelope
