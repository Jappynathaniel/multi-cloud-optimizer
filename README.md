# RedBridge FinOps

RedBridge is a read-only, multi-cloud FinOps API and dashboard. It collects
real provider billing facts, plus AWS EC2 inventory and native rightsizing
findings, stores the evidence, creates deterministic recommendations, and uses
an optional AI agent only to explain established data. It never executes a
cloud-provider change.

## Product boundary

- **Does:** collect cost/inventory data; retain evidence; surface provider
  rightsizing findings; detect safe policy candidates; prepare review material.
- **Does not:** accept credentials in normal workload requests; fabricate
  savings; let an agent mutate cloud resources; auto-approve a change.

## Run locally

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
export REDBRIDGE_ENCRYPTION_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
.venv/bin/uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`. For Windows, use `.venv\\Scripts\\` instead of
`.venv/bin/`.

## Cloud onboarding

Create a connection with `POST /v1/connections`, then call
`POST /v1/connections/{id}/collect`.

### AWS

```json
{"name":"prod-aws","provider":"aws","config":{"role_arn":"arn:aws:iam::123456789012:role/RedBridgeReadOnly","external_id":"unique-value","region":"us-east-1"}}
```

Use a cross-account role that permits only EC2 describe, Cost Explorer
read/query, STS assume-role, and Compute Optimizer read actions. Cost Explorer
and Compute Optimizer must be enabled by the customer.

### Azure

```json
{"name":"prod-azure","provider":"azure","config":{"tenant_id":"...","client_id":"...","client_secret":"...","subscription_id":"..."}}
```

Use a service principal limited to Cost Management query and later add Resource
Graph, Monitor, and Advisor reader permissions as those collectors are enabled.

### GCP

```json
{"name":"prod-gcp","provider":"gcp","config":{"service_account":{...},"billing_table":"project.dataset.gcp_billing_export_v1_..."}}
```

Enable detailed Cloud Billing export to BigQuery first. The connection queries
the exported table, so it never makes up pricing from public price pages.

## Current provider coverage

AWS is the first end-to-end connector (EC2 inventory, Cost Explorer, and
Compute Optimizer). Azure Cost Management and GCP BigQuery Billing export are
live billing connectors; their Resource Graph/Monitor/Advisor and Cloud Asset
Inventory/Monitoring/Recommender enrichments are intentionally marked planned,
not represented as delivered capability. Check `/v1/capabilities` for the
machine-readable coverage matrix.

## Deploy to Render

1. Push this replacement to GitHub.
2. Create a Render Blueprint using `render.yaml`.
3. Set `REDBRIDGE_DATABASE_URL` to a managed Postgres URL.
4. Keep the generated `REDBRIDGE_ENCRYPTION_KEY`; set `REDBRIDGE_OPENAI_API_KEY`
   only if you want the explanation agent.

SQLite is for local development only. Production needs Postgres and a background
worker/cron service for scheduled collection jobs; the first release exposes
collection through the API to keep every run observable.

## Agent safety

The agent receives a selected recommendation and its evidence only. It has no
cloud provider functions and cannot access connection credentials. It can explain
assumptions, uncertainties, and what a human must verify before approval.

