import type {
  ChatHistory,
  ChatMessageResult,
  ChatSession,
} from "@/lib/chat-types";


const API_URL =
  process.env.NEXT_PUBLIC_SUPPORTPILOT_API_URL ??
  "http://127.0.0.1:8001";


async function parseApiResponse<T>(
  response: Response,
): Promise<T> {
  if (response.ok) {
    return response.json() as Promise<T>;
  }

  let message =
    "SupportPilot could not complete the request.";

  try {
    const body = await response.json();

    if (typeof body?.detail?.message === "string") {
      message = body.detail.message;
    }
  } catch {
    // Preserve safe generic error.
  }

  throw new Error(message);
}


export async function createChatSession(): Promise<ChatSession> {
  const response = await fetch(
    `${API_URL}/api/v1/chat/sessions`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    },
  );

  return parseApiResponse<ChatSession>(
    response,
  );
}


export async function sendChatMessage(
  session: ChatSession,
  clientMessageId: string,
  body: string,
  customerHint?: string,
): Promise<ChatMessageResult> {
  const response = await fetch(
    `${API_URL}/api/v1/chat/sessions/${session.session_id}/messages`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Chat-Session-Token":
          session.session_token,
      },
      body: JSON.stringify({
        client_message_id:
          clientMessageId,
        body,
        customer_hint:
          customerHint || null,
      }),
    },
  );

  return parseApiResponse<ChatMessageResult>(
    response,
  );
}


export async function getChatHistory(
  session: ChatSession,
): Promise<ChatHistory> {
  const response = await fetch(
    `${API_URL}/api/v1/chat/sessions/${session.session_id}/messages`,
    {
      method: "GET",
      headers: {
        "X-Chat-Session-Token":
          session.session_token,
      },
      cache: "no-store",
    },
  );

  return parseApiResponse<ChatHistory>(
    response,
  );
}