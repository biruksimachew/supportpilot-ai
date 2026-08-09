from uuid import UUID

import psycopg
from fastapi import (
    APIRouter,
    Header,
    HTTPException,
    Response,
    status,
)

from app.core.chat_security import (
    ChatSessionTokenError,
    create_chat_session,
    verify_chat_session_token,
)
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionResponse,
)
from app.services.chat import (
    get_chat_history,
    send_chat_message,
)


router = APIRouter(
    prefix="/api/v1/chat",
    tags=["chat"],
)


def require_valid_session(
    session_id: UUID,
    session_token: str,
) -> None:
    try:
        verify_chat_session_token(
            session_id,
            session_token,
        )
    except ChatSessionTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "INVALID_CHAT_SESSION",
                "message": (
                    "The chat session is invalid or expired."
                ),
            },
        ) from exc


@router.post(
    "/sessions",
    response_model=ChatSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_chat_session() -> ChatSessionResponse:
    try:
        (
            session_id,
            session_token,
            expires_at,
        ) = create_chat_session()

    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "CHAT_CONFIGURATION_ERROR",
                "message": (
                    "Chat sessions are temporarily unavailable."
                ),
            },
        ) from exc

    return ChatSessionResponse(
        session_id=session_id,
        session_token=session_token,
        expires_at=expires_at,
    )


@router.post(
    "/sessions/{session_id}/messages",
    response_model=ChatMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_chat_message(
    session_id: UUID,
    payload: ChatMessageRequest,
    response: Response,
    x_chat_session_token: str = Header(
        alias="X-Chat-Session-Token",
    ),
) -> ChatMessageResponse:
    require_valid_session(
        session_id,
        x_chat_session_token,
    )

    try:
        result = send_chat_message(
            session_id,
            payload,
        )

    except psycopg.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "CHAT_INTAKE_UNAVAILABLE",
                "message": (
                    "The message could not be persisted."
                ),
            },
        ) from exc

    if result.duplicate:
        response.status_code = (
            status.HTTP_200_OK
        )

    return result


@router.get(
    "/sessions/{session_id}/messages",
    response_model=ChatHistoryResponse,
)
def read_chat_history(
    session_id: UUID,
    x_chat_session_token: str = Header(
        alias="X-Chat-Session-Token",
    ),
) -> ChatHistoryResponse:
    require_valid_session(
        session_id,
        x_chat_session_token,
    )

    try:
        return get_chat_history(
            session_id
        )

    except psycopg.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "CHAT_HISTORY_UNAVAILABLE",
                "message": (
                    "Chat history is temporarily unavailable."
                ),
            },
        ) from exc