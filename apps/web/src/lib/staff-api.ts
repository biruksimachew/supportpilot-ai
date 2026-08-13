import type {
  AgentQueueResponse,
  AgentTicketDetail,
  TicketChannel,
  TicketPriority,
  TicketStatus,
  AgentDashboardResponse,
} from "@/lib/staff-types";


const API_URL =
  process.env
    .NEXT_PUBLIC_SUPPORTPILOT_API_URL
  ?? "http://127.0.0.1:8001";


export class StaffApiError
  extends Error {

  status: number;


  constructor(
    message: string,
    status: number,
  ) {
    super(message);

    this.name =
      "StaffApiError";

    this.status =
      status;
  }
}


async function parseResponse<T>(
  response: Response,
): Promise<T> {

  if (response.ok) {
    return (
      response.json() as Promise<T>
    );
  }


  let message =
    (
      "SupportPilot could not "
      + "complete the request."
    );


  try {

    const body =
      await response.json();


    if (
      typeof body?.detail?.message
      === "string"
    ) {
      message =
        body.detail.message;
    }

  } catch {
    // Preserve the safe generic
    // fallback message.
  }


  throw new StaffApiError(
    message,
    response.status,
  );
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
      String(
        filters.limit,
      ),
    );
  }


  if (
    typeof filters.offset
    === "number"
  ) {
    params.set(
      "offset",
      String(
        filters.offset,
      ),
    );
  }


  const query =
    params.toString();


  const response =
    await fetch(
      (
        `${API_URL}`
        + "/api/v1/agent/tickets"
        + (
          query
            ? `?${query}`
            : ""
        )
      ),

      {
        headers: {
          Authorization:
            `Bearer ${accessToken}`,
        },

        cache:
          "no-store",
      },
    );


  return parseResponse<
    AgentQueueResponse
  >(
    response,
  );
}


export async function getAgentTicket(
  accessToken: string,
  ticketId: string,

): Promise<AgentTicketDetail> {

  const response =
    await fetch(
      (
        `${API_URL}`
        + "/api/v1/agent/tickets/"
        + ticketId
      ),

      {
        headers: {
          Authorization:
            `Bearer ${accessToken}`,
        },

        cache:
          "no-store",
      },
    );


  return parseResponse<
    AgentTicketDetail
  >(
    response,
  );
}


export async function getAgentDashboard(
  accessToken: string,
): Promise<AgentDashboardResponse> {

  const response =
    await fetch(
      `${API_URL}/api/v1/agent/dashboard`,
      {
        headers: {
          Authorization:
            `Bearer ${accessToken}`,
        },

        cache:
          "no-store",
      },
    );


  return parseResponse<
    AgentDashboardResponse
  >(
    response,
  );
}