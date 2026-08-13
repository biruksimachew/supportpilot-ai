export type TicketStatus =
  | "NEW"
  | "TRIAGED"
  | "DRAFTED"
  | "AUTO_RESPONDED"
  | "REVIEW_REQUIRED"
  | "WAITING_CUSTOMER"
  | "RESOLVED"
  | "FAILED";


export type TicketPriority =
  | "P1"
  | "P2"
  | "P3"
  | "P4";


export type TicketChannel =
  | "chat"
  | "email";


export type ConfidenceBand =
  | "HIGH"
  | "MEDIUM"
  | "LOW";


export type AgentQueueItem = {
  id: string;
  reference: string;

  channel: TicketChannel;
  status: TicketStatus;
  priority: TicketPriority;

  intent: string | null;

  confidence_band:
    ConfidenceBand | null;

  customer_name:
    string | null;

  customer_email:
    string | null;

  assignee_name:
    string | null;

  created_at: string;
  updated_at: string;

  message_count: number;

  last_message_body:
    string | null;

  last_message_at:
    string | null;
};


export type AgentQueueResponse = {
  items: AgentQueueItem[];

  total: number;
  limit: number;
  offset: number;
};


export type AgentTicketMessage = {
  id: string;

  direction: string;
  sender_type: string;

  body: string;

  is_internal: boolean;

  sent_at: string;
  received_at: string;
};


export type AgentOrderSummary = {
  external_order_id: string;

  status: string;

  fulfillment_summary:
    Record<string, unknown>;

  total_summary:
    Record<string, unknown>;

  retrieved_at: string;
};


export type AgentAuditEvent = {
  id: string;

  actor_type: string;
  event_type: string;

  entity_type: string;
  entity_id: string;

  metadata:
    Record<string, unknown>;

  created_at: string;
};


export type AgentTicketDetail = {
  id: string;
  reference: string;

  channel: TicketChannel;
  status: TicketStatus;
  priority: TicketPriority;

  intent: string | null;

  confidence_band:
    ConfidenceBand | null;

  restricted_action: boolean;

  escalation_reason:
    string | null;

  resolution_code:
    string | null;

  created_at: string;
  updated_at: string;

  resolved_at:
    string | null;

  customer_id:
    string | null;

  customer_name:
    string | null;

  customer_email:
    string | null;

  assignee_id:
    string | null;

  assignee_name:
    string | null;

  messages:
    AgentTicketMessage[];

  orders:
    AgentOrderSummary[];

  audit_events:
    AgentAuditEvent[];
};