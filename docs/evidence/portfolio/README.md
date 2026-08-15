# SupportPilot AI â€” Portfolio Evidence Manifest

Generated: 2026-08-15T17:08:57.8345575Z
Git branch: main
Git commit: f490a05f39247213abd6bea2bf3e737dacb61bf9

## Automated runtime proof

- `runtime-services.txt` â€” Docker Compose service state.
- `health-live.json` â€” API process liveness.
- `health-ready.json` â€” database/pgvector readiness contract.
- `final-regression-api.txt` â€” complete API pytest regression.
- `final-regression-pgtap.txt` â€” database/RLS pgTAP regression.
- `final-web-lint.txt` â€” frontend lint gate.
- `final-web-build.txt` â€” production Next.js build gate.
- `milestone-evidence-inventory.json` â€” SHA-256 inventory of milestone evaluation evidence.

## Existing measured milestone evidence

- `../milestone-3-rag-evaluation.json` / `.txt`
- `../milestone-4-commerce-safety-evaluation.json` / `.txt`
- `../milestone-6a-adversarial-safety-evaluation.json` / `.txt`
- `../milestone-6b-reliability-performance.json` / `.txt`

## Screenshot set

Place curated public screenshots in `screenshots/` using these names:

1. `01-agent-queue.png`
2. `02-ticket-workspace.png`
3. `03-ai-decision.png`
4. `04-retrieval-evidence.png`
5. `05-verified-order-context.png`
6. `06-restricted-review.png`
7. `07-operations-dashboard.png`
8. `08-gmail-delivery-redacted.png`

See `docs/portfolio-evidence-guide.md` for capture guidance.

## Public-evidence rules

- Do not expose API keys, secrets, bearer tokens, cookies, local `.env` values, or service-role keys.
- Redact personal email addresses in the Gmail screenshot before committing it publicly.
- Prefer synthetic Northstar customer data in product screenshots.
- Do not modify historical milestone result files merely to make the final presentation cleaner.
