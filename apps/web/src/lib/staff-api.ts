import type {
  AgentDashboardResponse,
  AgentQueueResponse,
  AgentResolutionCode,
  AgentSendReplyResponse,
  AgentTicketDetail,
  AgentWorkflowResponse,
  TicketChannel,
  TicketPriority,
  TicketStatus,
} from "@/lib/staff-types";

const API_URL =
  process.env.NEXT_PUBLIC_SUPPORTPILOT_API_URL
  ?? "http://127.0.0.1:8001";

export class StaffApiError extends Error {
  status: number;
  code: string | null;

  constructor(
    message: string,
    status: number,
    code: string | null = null,
  ) {
    super(message);
    this.name = "StaffApiError";
    this.status = status;
    this.code = code;
  }
}

async function parseResponse<T>(
  response: Response,
): Promise<T> {
  if (response.ok) {
    return response.json() as Promise<T>;
  }

  let message =
    "SupportPilot could not complete the request.";
  let code: string | null = null;

  try {
    const body = await response.json();

    if (
      typeof body?.detail?.message === "string"
    ) {
      message = body.detail.message;
    }

    if (
      typeof body?.detail?.code === "string"
    ) {
      code = body.detail.code;
    }
  } catch {
    // Preserve the safe fallback.
  }

  throw new StaffApiError(
    message,
    response.status,
    code,
  );
}

function authHeaders(
  accessToken: string,
  includeJson = false,
): HeadersInit {
  return {
    Authorization:
      `Bearer ${accessToken}`,
    ...(includeJson
      ? {
          "Content-Type":
            "application/json",
        }
      : {}),
  };
}

export type QueueFilters = {
  status?: TicketStatus;
  priority?: TicketPriority;
  intent?: string;
  channel?: TicketChannel;
  includeResolved?: boolean;
  limit?: number;
  offset?: number;
};

export async function getAgentQueue(
  accessToken: string,
  filters: QueueFilters = {},
): Promise<AgentQueueResponse> {
  const params =
    new URLSearchParams();

  if (filters.status) {
    params.set(
      "status",
      filters.status,
    );
  }

  if (filters.priority) {
    params.set(
      "priority",
      filters.priority,
    );
  }

  if (filters.intent) {
    params.set(
      "intent",
      filters.intent,
    );
  }

  if (filters.channel) {
    params.set(
      "channel",
      filters.channel,
    );
  }

  if (filters.includeResolved) {
    params.set(
      "include_resolved",
      "true",
    );
  }

  if (
    typeof filters.limit
    === "number"
  ) {
    params.set(
      "limit",
      String(filters.limit),
    );
  }

  if (
    typeof filters.offset
    === "number"
  ) {
    params.set(
      "offset",
      String(filters.offset),
    );
  }

  const query =
    params.toString();

  const response =
    await fetch(
      `${API_URL}/api/v1/agent/tickets${
        query
          ? `?${query}`
          : ""
      }`,
      {
        headers:
          authHeaders(accessToken),
        cache:
          "no-store",
      },
    );

  return parseResponse<
    AgentQueueResponse
  >(response);
}

export async function getAgentTicket(
  accessToken: string,
  ticketId: string,
): Promise<AgentTicketDetail> {
  const response =
    await fetch(
      `${API_URL}/api/v1/agent/tickets/${ticketId}`,
      {
        headers:
          authHeaders(accessToken),
        cache:
          "no-store",
      },
    );

  return parseResponse<
    AgentTicketDetail
  >(response);
}

export async function getAgentDashboard(
  accessToken: string,
): Promise<AgentDashboardResponse> {
  const response =
    await fetch(
      `${API_URL}/api/v1/agent/dashboard`,
      {
        headers:
          authHeaders(accessToken),
        cache:
          "no-store",
      },
    );

  return parseResponse<
    AgentDashboardResponse
  >(response);
}

export async function addAgentInternalNote(
  accessToken: string,
  ticketId: string,
  body: string,
): Promise<AgentWorkflowResponse> {
  const response =
    await fetch(
      `${API_URL}/api/v1/agent/tickets/${ticketId}/notes`,
      {
        method:
          "POST",
        headers:
          authHeaders(
            accessToken,
            true,
          ),
        body:
          JSON.stringify({
            body,
          }),
      },
    );

  return parseResponse<
    AgentWorkflowResponse
  >(response);
}

export async function assignAgentTicketToSelf(
  accessToken: string,
  ticketId: string,
): Promise<AgentWorkflowResponse> {
  const response =
    await fetch(
      `${API_URL}/api/v1/agent/tickets/${ticketId}/assign-self`,
      {
        method:
          "POST",
        headers:
          authHeaders(accessToken),
      },
    );

  return parseResponse<
    AgentWorkflowResponse
  >(response);
}

export async function escalateAgentTicket(
  accessToken: string,
  ticketId: string,
  reason: string,
  priority?: TicketPriority,
): Promise<AgentWorkflowResponse> {
  const response =
    await fetch(
      `${API_URL}/api/v1/agent/tickets/${ticketId}/escalate`,
      {
        method:
          "POST",
        headers:
          authHeaders(
            accessToken,
            true,
          ),
        body:
          JSON.stringify({
            reason,
            priority:
              priority ?? null,
          }),
      },
    );

  return parseResponse<
    AgentWorkflowResponse
  >(response);
}

export async function resolveAgentTicket(
  accessToken: string,
  ticketId: string,
  resolutionCode:
    AgentResolutionCode,
): Promise<AgentWorkflowResponse> {
  const response =
    await fetch(
      `${API_URL}/api/v1/agent/tickets/${ticketId}/resolve`,
      {
        method:
          "POST",
        headers:
          authHeaders(
            accessToken,
            true,
          ),
        body:
          JSON.stringify({
            resolution_code:
              resolutionCode,
          }),
      },
    );

  return parseResponse<
    AgentWorkflowResponse
  >(response);
}

export async function sendAgentReply(
  accessToken: string,
  ticketId: string,
  idempotencyKey: string,
  body: string,
): Promise<AgentSendReplyResponse> {
  const response =
    await fetch(
      `${API_URL}/api/v1/agent/tickets/${ticketId}/send`,
      {
        method:
          "POST",
        headers:
          authHeaders(
            accessToken,
            true,
          ),
        body:
          JSON.stringify({
            idempotency_key:
              idempotencyKey,
            body,
          }),
      },
    );

  return parseResponse<
    AgentSendReplyResponse
  >(response);
}
