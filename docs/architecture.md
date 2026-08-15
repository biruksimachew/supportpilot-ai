# SupportPilot AI Architecture

This document describes the implemented portfolio architecture for SupportPilot AI. Northstar Commerce Co. is fictional and all public/demo data is synthetic.

## 1. System context

```mermaid
flowchart LR
    Customer --> Web[Next.js customer chat]
    Agent[Support agent / manager] --> Web
    Gmail --> N8N[n8n workflows]

    Web --> API[FastAPI support core]
    N8N --> API
    API --> Postgres[(Supabase PostgreSQL)]
    Postgres --- PGV[(pgvector)]
    API --> Embed[FastEmbed]
    API --> LLM[Ollama qwen3:1.7b]
    API --> Commerce[Read-only commerce mock]
    API --> N8N
    N8N --> Gmail
```

### Responsibilities

| Component | Responsibility |
|---|---|
| Next.js web app | Customer chat, authenticated staff queue, ticket detail, decision/evidence/audit views, operations dashboard |
| FastAPI | Ticket/channel API, safety policy, RAG orchestration, identity verification, commerce lookup, outbound delivery semantics |
| Supabase/PostgreSQL | Auth-linked staff profiles, tickets, messages, knowledge metadata, AI runs, evidence, tool calls, actions, audit events, deliveries |
| pgvector | Similarity retrieval over indexed knowledge chunks |
| FastEmbed | Local embedding provider (`BAAI/bge-small-en-v1.5`) |
| Ollama | Local grounded generation (`qwen3:1.7b`) |
| Commerce mock | Synthetic Shopify-style, read-only customer/order/product facts |
| n8n | Gmail intake/outbound orchestration and local OAuth integration |
| Gmail | Shared-inbox-style intake and demonstrated outbound delivery |

Slack escalation was a SHOULD requirement in the simulated brief and is intentionally documented as deferred rather than claimed as implemented.

## 2. Trust boundaries

```mermaid
flowchart TB
    subgraph Untrusted[Untrusted / external inputs]
      CM[Customer message]
      EM[Email MIME/content]
      KD[Knowledge document content]
    end

    subgraph Control[SupportPilot application control plane]
      INT[Intake + persistence]
      POL[Restricted-action + policy gates]
      ID[Identity gate]
      RET[Published-only retrieval]
      VAL[Grounding/output validation]
      AUD[Audit + idempotency]
    end

    subgraph Providers[Bounded providers]
      EMB[Embedding provider]
      GEN[Generation provider]
      COM[Read-only commerce provider]
      MAIL[Email delivery provider]
    end

    Untrusted --> INT --> POL
    POL --> ID
    POL --> RET
    ID --> COM
    RET --> EMB
    RET --> GEN
    GEN --> VAL
    COM --> VAL
    VAL --> AUD
    AUD --> MAIL
```

Customer messages and retrieved documents are treated as data, not authority. Provider output is not trusted until it satisfies the application's structured contract.

## 3. Knowledge/RAG path

```mermaid
sequenceDiagram
    participant U as Customer / Agent
    participant A as FastAPI
    participant E as FastEmbed
    participant V as pgvector
    participant G as Ollama
    participant D as PostgreSQL

    U->>A: Knowledge question
    A->>D: Persist ticket/message
    A->>E: Embed normalized query
    E-->>A: Query vector
    A->>V: Retrieve published chunks
    V-->>A: Ranked evidence
    A->>A: Evidence confidence/conflict gate

    alt evidence insufficient / ambiguous / conflicting
        A->>D: Persist REVIEW_REQUIRED + reasons
        A-->>U: Safe review/escalation outcome
    else evidence allowed
        A->>G: Grounded prompt + evidence refs
        G-->>A: Structured answer + citations
        A->>A: Validate answer/citation contract
        alt valid
            A->>D: Persist AI run + evidence + draft
            A-->>U: Safe draft/decision
        else invalid after bounded retry
            A->>D: Persist grounding failure + review
            A-->>U: Human-review outcome
        end
    end
```

Key properties:

- only published knowledge is retrieved for normal support answers;
- evidence confidence, ambiguity and conflict are application-level signals;
- generation is skipped when evidence does not allow it;
- generation attempts are bounded;
- citations must reference retrieved evidence;
- invalid structured output fails closed.

## 4. Restricted-action path

```mermaid
sequenceDiagram
    participant C as Customer
    participant A as FastAPI
    participant P as Restricted-action policy
    participant D as PostgreSQL
    participant S as Staff UI

    C->>A: "Refund #NS10042 now"
    A->>D: Persist inbound message
    A->>P: Normalize + classify restricted operation
    P-->>A: REFUND / restricted
    Note over A: No commerce write tool exists
    Note over A: RAG/generation not required for the action decision
    A->>D: Persist REVIEW_REQUIRED, reasons, priority/escalation
    S->>A: Load ticket detail
    A-->>S: Restricted action + decision + audit
```

The AI cannot grant itself refund, cancellation, order-edit, address-change, payment, policy-exception, or replacement authority because those write capabilities do not exist in the MVP tool surface.

## 5. Order-status path

```mermaid
flowchart TD
    Q[Order-specific question] --> N{Order number present?}
    N -->|No| C[Request clarification]
    N -->|Yes| I{Identity verified for that order?}
    I -->|No| C
    I -->|Yes| L[Read-only commerce lookup]
    L --> S{Lookup succeeds and remains in scope?}
    S -->|No| R[Review / temporary inability]
    S -->|Yes| F[Attach minimal order facts]
    F --> D[Persist tool call + safe draft decision]
```

The provider returns a deliberately narrow support view. Cross-customer and failed-verification cases must not expose order contents, fulfillment state, tracking data, or totals.

## 6. Email path

### Intake

```mermaid
flowchart LR
    G[Gmail Trigger] --> GET[Get message]
    GET --> N[Normalize SupportPilot email]
    N -->|Integration secret| API[FastAPI email intake]
    API --> D[(PostgreSQL)]
```

### Outbound

```mermaid
flowchart LR
    S[Agent controlled send] --> API[FastAPI delivery service]
    API -->|idempotency key| D[(outbound_deliveries)]
    API --> N[n8n]
    N --> G[Gmail reply]
    G -->|provider result| API
    API -->|DELIVERED / FAILED / UNCERTAIN| D
```

Confirmed failure and ambiguous delivery are intentionally distinct. An ambiguous provider result is not silently treated as safe to retry.

## 7. Data and audit model

The core schema includes staff/users, customers, tickets, messages, cached order context, knowledge sources/chunks, AI runs, retrieval evidence, tool calls, agent actions and audit events. Delivery records extend the operational trail for outbound responses.

Material AI decisions persist provider/model/prompt metadata, intent, confidence band, decision reasons, latency/error information and linked evidence/tool activity. Staff actions and ticket transitions are also recorded.

## 8. Security model

- Staff interfaces require authentication.
- Server-side role checks and PostgreSQL RLS protect internal tables.
- Browser-authenticated staff are not given direct mutation authority over sensitive tables; mutations go through API workflows.
- Secrets live in environment/local integration configuration and are excluded from public evidence.
- Commerce is read-only and identity scoped.
- Customer-facing output excludes internal confidence, prompts, tool names and excessive PII.
- Readiness fails closed when core database/vector dependencies are unavailable.

## 9. Provider boundaries

Embeddings, generation and commerce access are abstracted so integration tests can substitute deterministic providers. This is why safety and acceptance gates can be tested without relying on a paid API or nondeterministic external model behavior.

The local demo uses FastEmbed and Ollama. The 384-dimensional native local embedding is adapted to the project's 1536-dimensional vector contract; a production deployment should choose one consistent native dimension/index contract rather than carry this compatibility layer.

## 10. Observed performance

The measured local full grounded RAG decision p95 was about 6.33 seconds, with local model generation accounting for most of the observed latency. Verified commerce decisions were below one second p95 in the captured M6B sample.

These are local portfolio measurements, not production SLAs. See `docs/evidence/milestone-6b-reliability-performance.*` for the recorded report.
