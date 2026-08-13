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


export type DashboardDistributionItem = {
  key: string;
  count: number;
};


export type DashboardQueueSummary = {
  open_tickets: number;
  review_required: number;
  waiting_customer: number;
  drafted: number;
  new_tickets: number;
  urgent_p1_p2: number;
  unassigned: number;
  restricted_open: number;
};


export type DashboardAISummary = {
  total_runs: number;
  auto_respond: number;
  review_required: number;
  request_clarification: number;
  failed: number;

  automation_rate_pct:
    number | null;
};


export type DashboardDeliverySummary = {
  total_deliveries: number;
  delivered: number;
  failed: number;
  uncertain: number;
  pending: number;

  delivery_success_rate_pct:
    number | null;
};


export type DashboardResolutionSummary = {
  resolved_tickets: number;

  average_resolution_minutes:
    number | null;
};


export type DashboardActivityItem = {
  id: string;

  actor_type: string;

  event_type: string;

  ticket_id:
    string | null;

  ticket_reference:
    string | null;

  created_at: string;
};


export type AgentDashboardResponse = {
  generated_at: string;

  queue:
    DashboardQueueSummary;

  status_breakdown:
    DashboardDistributionItem[];

  priority_breakdown:
    DashboardDistributionItem[];

  channel_breakdown:
    DashboardDistributionItem[];

  intent_breakdown:
    DashboardDistributionItem[];

  escalation_breakdown:
    DashboardDistributionItem[];

  ai:
    DashboardAISummary;

  delivery:
    DashboardDeliverySummary;

  resolution:
    DashboardResolutionSummary;

  recent_activity:
    DashboardActivityItem[];
};