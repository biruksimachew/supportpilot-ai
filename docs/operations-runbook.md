# SupportPilot AI Operations Runbook

This runbook covers the local portfolio environment: start/stop, resets, health checks, common failures, safe retries, evidence capture and secret handling.

> Northstar Commerce Co. and all committed business data are fictional/synthetic. Do not place real customer data or real credentials in repository files or screenshots.

## 1. Local services

| Surface | Default |
|---|---|
| Web app | `http://127.0.0.1:3000` |
| FastAPI | `http://127.0.0.1:8001` |
| API liveness | `http://127.0.0.1:8001/health/live` |
| API readiness | `http://127.0.0.1:8001/health/ready` |
| n8n | `http://localhost:5680` |
| Ollama host port | `11435` |
| Supabase API | `55321` |
| Supabase Postgres | `55322` |
| Supabase Studio | `55323` |
| Supabase Mailpit | `55324` |

The commerce mock is container-internal on port `8080` and is not intended to be a public host service.

## 2. Normal startup

From repository root:

```powershell
npx supabase start

docker compose up -d --build

docker compose ps
```

If the Ollama model is not installed in the persistent volume:

```powershell
docker compose exec -T ollama `
  ollama pull qwen3:1.7b
```

Start the web app in a separate PowerShell window:

```powershell
Set-Location .\apps\web
npm ci
npm run dev
```

## 3. First-time / clean reset

A database reset destroys current local ticket/audit/demo state. Do not run it merely to refresh screenshots.

```powershell
npx supabase db reset
python .\scripts\bootstrap_staff.py

docker compose exec -T api `
  python -m scripts.index_published_knowledge

docker compose exec -T api `
  python -m scripts.bootstrap_demo_queue
```

Use synthetic credentials only for the demo account.

## 4. Health checks

```powershell
Invoke-RestMethod `
  -Uri http://127.0.0.1:8001/health/live

Invoke-RestMethod `
  -Uri http://127.0.0.1:8001/health/ready
```

Expected healthy states:

- liveness: `status = ok`
- readiness: `status = ready`
- readiness dependencies: database and pgvector true

A readiness `503` is expected fail-closed behavior when database/vector dependencies are unavailable.

## 5. Logs

```powershell
docker compose logs api --tail 200

docker compose logs n8n --tail 200

docker compose logs commerce-mock --tail 200

docker compose logs ollama --tail 200
```

Avoid copying full logs into public issues/evidence without checking for addresses, tokens, request payloads and provider metadata.

## 6. Standard regression gates

Backend:

```powershell
docker compose exec -T api `
  python -m pytest -q -p no:cacheprovider
```

Use `python -m pytest`; this is the canonical invocation for the containerized project.

Database/RLS:

```powershell
npx supabase test db
```

Frontend:

```powershell
Set-Location .\apps\web
npm run lint
npm run build
```

Known non-failing warning: Starlette currently emits a `TestClient`/`httpx` deprecation warning. Do not casually upgrade core dependencies only to silence it after the final regression suite is green.

## 7. Knowledge indexing

Re-index published sources after a reset or approved knowledge change:

```powershell
docker compose exec -T api `
  python -m scripts.index_published_knowledge
```

Normal retrieval should only use published sources. If retrieval unexpectedly returns nothing, check:

1. API readiness;
2. that published sources exist;
3. that knowledge chunks have embeddings;
4. FastEmbed cache/provider startup;
5. configured evidence thresholds.

Do not answer policy questions from model memory when retrieval is unavailable.

## 8. Ollama / generation problems

Check model availability:

```powershell
docker compose exec -T ollama ollama list
```

Pull model if missing:

```powershell
docker compose exec -T ollama `
  ollama pull qwen3:1.7b
```

If generation times out or returns malformed output, the application is expected to persist a failure/review outcome rather than silently fabricate a customer response. Do not bypass the grounding validator to make a demo pass.

## 9. Commerce failures

The commerce mock is intentionally read-only. Health:

```powershell
docker compose exec -T commerce-mock `
  python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8080/health/live').read().decode())"
```

If commerce is unavailable:

- do not invent order status;
- keep identity gating in force;
- route/clarify according to the persisted decision;
- never add a temporary write-capable order/refund endpoint as a workaround.

## 10. Gmail / n8n

Open n8n at `http://localhost:5680`.

Gmail OAuth credentials are local environment state and are not portable repository configuration. After importing/recreating a workflow, rebind the Gmail credential inside n8n.

For outbound delivery:

- `DELIVERED` means the provider path returned a confirmed success;
- `FAILED` means a confirmed failure;
- `UNCERTAIN` means the provider outcome was ambiguous.

### Critical retry rule

**Do not blindly retry an `UNCERTAIN` delivery.** Confirm whether Gmail already accepted/sent the message before issuing another attempt. Reuse the same idempotency semantics when reconciliation determines that a retry is safe.

## 11. PowerShell `npx` stderr behavior

Windows PowerShell 5.1 can surface harmless native-process stderr as a `NativeCommandError`, including Supabase CLI status text such as “Connecting to local database...”.

For automation scripts, judge the native command by its exit code, not by the presence of stderr text alone. The final portfolio evidence capture already follows this pattern.

## 12. Evidence capture

The canonical final capture script is:

```powershell
powershell -ExecutionPolicy Bypass `
  -File .\scripts\capture_portfolio_evidence.ps1
```

Canonical output location:

```text
docs\evidence\portfolio
```

The capture records service state, health/readiness, backend tests, pgTAP, frontend lint/build and an evidence manifest. Screenshots live under:

```text
docs\evidence\portfolio\screenshots
```

Do not replace machine-readable evaluation files with screenshots of terminal output; keep both types of evidence for different purposes.

## 13. Shutdown

Stop Docker Compose services:

```powershell
docker compose down
```

Stop Supabase separately:

```powershell
npx supabase stop
```

Use volume removal only when intentionally destroying local service state.

## 14. Secret handling / public-repo checklist

Before a public push:

```powershell
git status --short

git ls-files | Select-String `
  -Pattern '\.env$|\.env\.local$|\.pem$|\.key$|credentials|token'
```

Also inspect staged content for common secret markers:

```powershell
git diff --cached | Select-String `
  -Pattern 'OPENAI_API_KEY|SERVICE_ROLE_KEY|N8N_ENCRYPTION_KEY|client_secret|access_token|refresh_token'
```

The presence of variable names in `.env.example` or documentation is expected; real values are not.

Before committing screenshots, confirm that they contain only synthetic SupportPilot/Northstar data. Any Gmail proof must be cropped/redacted to remove unrelated inbox content and personal/account details.

## 15. Common recovery order

When the local stack behaves unexpectedly, recover in this order instead of changing multiple components at once:

1. `docker compose ps`
2. API `/health/live`
3. API `/health/ready`
4. `npx supabase status`
5. relevant service logs
6. focused test for the failing area
7. full backend regression only after the focused problem is fixed
8. frontend lint/build if UI code changed

Do not reset the database, change dependency versions, or recreate OAuth credentials unless the evidence points to those layers.

## 16. Portfolio-safe limitations

- Prompt-injection handling is deterministic common-pattern hardening, not universal prevention.
- `AUTO_RESPOND` is an authorization decision; the project does not claim a fully autonomous production sender.
- Gmail attachment/MIME processing is intentionally limited compared with a mature help-desk platform.
- The operator reconciliation experience for every possible `UNCERTAIN` delivery outcome is not a complete production console.
- Slack escalation notification remains deferred.
- The local FastEmbed 384→1536 compatibility adapter should be standardized in a production vector architecture.
- Performance evidence is local/sample-specific.
