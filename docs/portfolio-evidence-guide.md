# SupportPilot AI â€” Portfolio Evidence Capture Guide

This guide defines the small public screenshot set for the SupportPilot AI portfolio case study.

The goal is not to screenshot every screen. The goal is to prove the operational system, safety controls, evidence grounding, commerce controls, and real delivery path with a compact set of high-signal images.

## Capture setup

Before taking screenshots:

1. Start the application stack.
2. Use the seeded/synthetic Northstar demo tickets where possible.
3. Use a desktop browser width around 1440â€“1600 px.
4. Keep the browser zoom at 100%.
5. Avoid showing browser extensions, unrelated tabs, terminal secrets, or local environment variables.
6. Make sure the staff shell is visible so screenshots clearly belong to the same product.

Save screenshots under:

`docs/evidence/portfolio/screenshots/`

## Required screenshots

### 01-agent-queue.png
Route: `/staff`

Capture the queue-only layout, filters, summary cards, and several seeded tickets.

### 02-ticket-workspace.png
Route: `/staff/tickets/<ticket-id>`

Capture the dedicated ticket page, conversation, composer, context rail, and action controls.

### 03-ai-decision.png
Use a ticket with an AI run and open the AI Decision tab.

Capture intent, confidence, decision, reasons, and safe-draft/auto-response eligibility where visible.

### 04-retrieval-evidence.png
Open Evidence on a ticket with an AI run.

Capture source title, section, score, and evidence content.

### 05-verified-order-context.png
Use a synthetic verified order-status ticket.

Capture verification status plus order/fulfillment/tracking context.

### 06-restricted-review.png
Use a synthetic refund/cancellation/replacement request.

Capture REVIEW_REQUIRED state, safety/review reason, and human action controls.

### 07-operations-dashboard.png
Route: `/staff/dashboard`

Capture queue health, AI decision summary, delivery summary, distributions, and recent activity if populated.

### 08-gmail-delivery-redacted.png
Use the successful real Gmail delivery evidence from M5.

Before committing, crop/redact personal addresses, unrelated inbox content, and account details.

## Recommended portfolio selection

Keep all eight in repository evidence if useful, but the eventual portfolio case study probably needs only five or six:
1. Queue
2. Ticket workspace
3. AI decision/evidence
4. Verified order context
5. Operations dashboard
6. Redacted Gmail proof

## What not to publish

Never commit:
- `.env`
- OAuth secrets
- Supabase service-role keys
- Gmail credentials/tokens
- bearer tokens
- raw personal inbox screenshots
- personal email addresses that are not intentionally public

