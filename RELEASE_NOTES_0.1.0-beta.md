# MOVA Tool SDK 0.1.0 Beta

## Summary

`mova-tool-sdk 0.1.0 beta` is the first public Python/CLI release of the MOVA SDK.

This release gives agents and developers a thin, honest entrypoint into the deployed MOVA State API:

- public beta identity
- contract registry access
- run creation and status tracking
- run diagnostics and artifact access
- authoring, lab, evidence, and promotion routes
- local `Forge` candidate generation and handoff

## Included in this beta

- Python client entrypoint: `Mova`
- local intent-to-candidate helper: `Forge`
- CLI command surface via `mova`
- public identity support:
  - `POST /v1/register`
  - `GET /v1/me`
  - `POST /v1/api-keys`
- runtime diagnostics support:
  - run artifacts
  - admission result
  - dispatch result
  - execute-dry result
  - execute-internal result
  - continuation result
  - runtime eligibility
  - access grant
- contract lifecycle support:
  - list
  - get
  - history
  - lineage
  - publish
  - deprecate
  - retire
  - reactivate
- business connector and binding routes
- GitHub Actions CI:
  - `pytest -q`
  - `python -m build`

## Verified before release prep

- local test suite: `27 passed`
- package build: `python -m build` passed
- live SDK smoke against deployed `MOVA State API` passed

Live smoke covered:

- `auth register`
- `auth me`
- `auth issue-key`
- `contracts list`
- `execute --contract-id invoice_ocr_contract_v0`
- `status`

Verified live run:

- run id: `8ec2f81e-16f5-4cbe-9b0a-f03286aa3a58`
- final status: `ENGINE_INTERNAL_INVOKED`
- final phase: `ENGINE_INTERNAL_INVOCATION_ACCEPTED`

## Not in scope for 0.1.0 beta

- billing
- teams / organizations for public users
- OAuth / password auth
- full product route coverage
- fully stable GA compatibility guarantees

## Compatibility note

This beta is designed against the current deployed MOVA State API surface and should be treated as an early public integration layer, not a final frozen SDK contract.
