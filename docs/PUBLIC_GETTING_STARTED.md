# Public Getting Started

## What This SDK Is

`mova-tool-sdk` is the public Python and CLI entrypoint for the MOVA State API.

Use it when you want to:

- register a public beta account
- mint a personal API key
- inspect contracts
- start execution runs
- read run status and diagnostics
- generate a local candidate package with `Forge`

## Install

Until package publication is completed, use the repo directly:

```bash
git clone https://github.com/mova-compact/mova-tool-sdk.git
cd mova-tool-sdk
python -m pip install -e .
```

After publication, install from Python package distribution:

```bash
pip install mova-tool-sdk
```

## Point The SDK At MOVA

Set the public API base URL:

```bash
export MOVA_PLATFORM_URL="https://engine15-mcp-door-v0.s-myasoedov81.workers.dev"
```

On Windows PowerShell:

```powershell
$env:MOVA_PLATFORM_URL = "https://engine15-mcp-door-v0.s-myasoedov81.workers.dev"
```

## First Login Flow

Register:

```bash
mova auth register you@example.com --set-key
```

Inspect the current identity:

```bash
mova auth me
```

Issue a narrower personal key if needed:

```bash
mova auth issue-key --scopes self_read,runs_write,runs_read,contracts_read,contracts_write --set-key
```

## First Read Calls

List contracts:

```bash
mova contracts list
```

Get one contract:

```bash
mova contracts get invoice_ocr_contract_v0
```

## First Execution Run

Run a deployed contract:

```bash
mova execute \
  --contract-id invoice_ocr_contract_v0 \
  --tenant-id YOUR_TENANT_ID \
  --caller-id sdk.quickstart \
  --input '{"source":"quickstart"}'
```

Check status:

```bash
mova status RUN_ID
```

Inspect runtime diagnostics:

```bash
mova status RUN_ID --view admission
mova status RUN_ID --view dispatch
mova status RUN_ID --view dry
mova status RUN_ID --view internal
mova status RUN_ID --view eligibility
mova status RUN_ID --view access-grant
```

## Forge Flow

Generate a local candidate package:

```bash
mova forge --intent "automate invoice processing with human approval" --output ./my-contract
```

Validate the local package:

```bash
mova validate ./my-contract
```

Inspect the local package:

```bash
mova inspect ./my-contract
```

Hand the candidate into the platform:

```bash
mova handoff \
  --form-ref authoring_form_v0 \
  --candidate-file ./my-contract/sdk_local_candidate_handoff_v2.json
```

## Current Beta Boundaries

This SDK is intentionally thin.

It is the correct public path for:

- identity
- contract inspection
- run creation
- run diagnostics
- authoring/lab/promotion handoff

It is not yet the final GA shape for every MOVA platform route.
