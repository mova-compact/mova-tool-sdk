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
- `mova forge`
- `mova validate`
- `mova inspect`
- `mova execute`
- `mova status`
- `mova decide`
- `mova audit`
- `mova connectors list`
- `mova connectors add`
- `mova connectors test`
- `mova connectors registered`
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
The first remote slice is already wired against the current bridge-compatible platform surface:

- `mova execute` registers a local contract package and starts a run
- `mova status` reads run state
- `mova audit` exports the run audit bundle
- `mova decide` maps to operator approve/deny actions

For local smoke and development, the API target can be overridden without writing user config:

- `MOVA_BASE_URL`
- `MOVA_RUNTIME_EXECUTE_TOKEN`
- `MOVA_ADMIN_READ_TOKEN`
- `MOVA_OPERATOR_RECOVERY_TOKEN`
