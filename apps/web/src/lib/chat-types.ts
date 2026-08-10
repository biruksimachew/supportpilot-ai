export type ChatSession = {
  session_id: string;
  session_token: string;
  expires_at: string;
};

export type ChatMessageResult = {
  ticket_id: string;
  ticket_reference: string;
  ticket_status: string;
  message_id: string;
  duplicate: boolean;
  created_ticket: boolean;
};

export type ChatHistoryMessage = {
  id: string;
  direction: "inbound" | "outbound";
  sender_type: "customer" | "ai" | "agent" | "system";
  body: string;
  sent_at: string;
};

export type ChatHistory = {
  session_id: string;
  ticket_reference: string | null;
  ticket_status: string | null;
  messages: ChatHistoryMessage[];
};