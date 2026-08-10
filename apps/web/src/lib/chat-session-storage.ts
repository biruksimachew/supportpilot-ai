import type {
  ChatSession,
} from "@/lib/chat-types";


const STORAGE_KEY =
  "supportpilot.chat.session.v1";


export function loadStoredSession():
  ChatSession | null {
  if (typeof window === "undefined") {
    return null;
  }

  const raw =
    window.sessionStorage.getItem(
      STORAGE_KEY,
    );

  if (!raw) {
    return null;
  }

  try {
    const session =
      JSON.parse(raw) as ChatSession;

    const expiresAt =
      new Date(
        session.expires_at,
      ).getTime();

    if (
      !session.session_id ||
      !session.session_token ||
      Number.isNaN(expiresAt) ||
      expiresAt <= Date.now()
    ) {
      clearStoredSession();
      return null;
    }

    return session;
  } catch {
    clearStoredSession();
    return null;
  }
}


export function storeSession(
  session: ChatSession,
): void {
  window.sessionStorage.setItem(
    STORAGE_KEY,
    JSON.stringify(session),
  );
}


export function clearStoredSession(): void {
  if (typeof window === "undefined") {
    return;
  }

  window.sessionStorage.removeItem(
    STORAGE_KEY,
  );
}