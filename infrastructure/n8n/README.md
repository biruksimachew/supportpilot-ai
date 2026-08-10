# SupportPilot AI — n8n Orchestration

n8n provides the external-channel orchestration layer for SupportPilot AI.

The current Milestone 2 workflow connects a Gmail support inbox to the canonical SupportPilot ticket intake API.

## Gmail Intake Workflow

Workflow:

`workflows/supportpilot-gmail-intake.json`

Flow:

```text
Gmail Trigger
    |
    v
Gmail Get Message
    |
    v
Normalize SupportPilot Email
    |
    v
POST /api/v1/integrations/email/messages
    |
    v
Canonical Ticket + Message Intake