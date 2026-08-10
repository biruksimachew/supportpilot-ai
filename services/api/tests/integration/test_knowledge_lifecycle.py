from uuid import (
    UUID,
    uuid4,
)

import psycopg

from fastapi.testclient import (
    TestClient,
)

from app.core.auth import (
    get_current_internal_user,
)

from app.core.config import (
    settings,
)

from app.main import app

from app.schemas.auth import (
    InternalUser,
)


client = TestClient(app)


MANAGER_ID = UUID(
    "22222222-2222-4222-8222-222222222222"
)

AGENT_ID = UUID(
    "33333333-3333-4333-8333-333333333333"
)


def fake_manager() -> InternalUser:
    return InternalUser(
        id=MANAGER_ID,
        email="manager@test.local",
        name="Knowledge Test Manager",
        role="SUPPORT_MANAGER",
    )


def fake_agent() -> InternalUser:
    return InternalUser(
        id=AGENT_ID,
        email="agent@test.local",
        name="Knowledge Test Agent",
        role="SUPPORT_AGENT",
    )


def cleanup_source(
    source_id: str,
) -> None:
    with psycopg.connect(
        settings.database_url
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                delete
                from public.audit_events

                where entity_type =
                    'knowledge_source'

                  and entity_id = %s;
                """,
                (
                    source_id,
                ),
            )

            cursor.execute(
                """
                delete
                from public.knowledge_sources

                where id = %s;
                """,
                (
                    source_id,
                ),
            )


def test_support_agent_cannot_manage_knowledge() -> None:
    app.dependency_overrides[
        get_current_internal_user
    ] = fake_agent

    try:
        response = client.post(
            "/api/v1/agent/knowledge/sources",
            json={
                "title":
                    f"Forbidden Source {uuid4()}",

                "type":
                    "FAQ",

                "version":
                    "1.0",

                "sections": [
                    {
                        "section":
                            "Question",

                        "content":
                            "Approved answer.",
                    }
                ],
            },
        )

        assert (
            response.status_code
            == 403
        )

        assert (
            response.json()[
                "detail"
            ][
                "code"
            ]
            ==
            "KNOWLEDGE_MANAGEMENT_FORBIDDEN"
        )

    finally:
        app.dependency_overrides.clear()


def test_knowledge_source_lifecycle() -> None:
    unique_suffix = str(
        uuid4()
    )

    source_id: str | None = None

    app.dependency_overrides[
        get_current_internal_user
    ] = fake_manager

    try:
        created = client.post(
            "/api/v1/agent/knowledge/sources",
            json={
                "title":
                    (
                        "M3A Test Returns Policy "
                        + unique_suffix
                    ),

                "type":
                    "POLICY",

                "version":
                    "1.0",

                "sections": [
                    {
                        "section":
                            "Eligibility",

                        "content":
                            (
                                "Unused items may be "
                                "returned within "
                                "30 days."
                            ),
                    },
                    {
                        "section":
                            "Condition",

                        "content":
                            (
                                "Returned products "
                                "must be unused."
                            ),
                    },
                ],

                "metadata": {
                    "test":
                        True,
                },
            },
        )

        assert (
            created.status_code
            == 201
        )

        created_result = (
            created.json()
        )

        source_id = (
            created_result["id"]
        )

        assert (
            created_result["status"]
            == "DRAFT"
        )

        assert (
            created_result[
                "section_count"
            ]
            == 2
        )

        assert len(
            created_result[
                "checksum"
            ]
        ) == 64

        original_checksum = (
            created_result[
                "checksum"
            ]
        )


        # --------------------------------------------------
        # Agent cannot see draft source.
        # --------------------------------------------------

        app.dependency_overrides[
            get_current_internal_user
        ] = fake_agent

        draft_as_agent = client.get(
            (
                "/api/v1/agent/knowledge/sources/"
                + source_id
            )
        )

        assert (
            draft_as_agent.status_code
            == 404
        )


        # --------------------------------------------------
        # Manager may edit draft.
        # --------------------------------------------------

        app.dependency_overrides[
            get_current_internal_user
        ] = fake_manager

        updated = client.put(
            (
                "/api/v1/agent/knowledge/sources/"
                + source_id
            ),
            json={
                "title":
                    (
                        "M3A Test Returns Policy "
                        + unique_suffix
                    ),

                "type":
                    "POLICY",

                "version":
                    "1.0",

                "sections": [
                    {
                        "section":
                            "Eligibility",

                        "content":
                            (
                                "Unused items may be "
                                "returned within "
                                "30 calendar days."
                            ),
                    }
                ],

                "metadata": {
                    "test":
                        True,

                    "reviewed":
                        True,
                },
            },
        )

        assert (
            updated.status_code
            == 200
        )

        updated_result = (
            updated.json()
        )

        assert (
            updated_result[
                "section_count"
            ]
            == 1
        )

        assert (
            updated_result[
                "checksum"
            ]
            != original_checksum
        )


        # --------------------------------------------------
        # Explicit publish.
        # --------------------------------------------------

        published = client.post(
            (
                "/api/v1/agent/knowledge/sources/"
                + source_id
                + "/publish"
            )
        )

        assert (
            published.status_code
            == 200
        )

        published_result = (
            published.json()
        )

        assert (
            published_result[
                "status"
            ]
            == "PUBLISHED"
        )

        assert (
            published_result[
                "effective_at"
            ]
            is not None
        )


        # --------------------------------------------------
        # Agent can now read it.
        # --------------------------------------------------

        app.dependency_overrides[
            get_current_internal_user
        ] = fake_agent

        published_as_agent = client.get(
            (
                "/api/v1/agent/knowledge/sources/"
                + source_id
            )
        )

        assert (
            published_as_agent.status_code
            == 200
        )


        # --------------------------------------------------
        # Published content cannot be edited.
        # --------------------------------------------------

        app.dependency_overrides[
            get_current_internal_user
        ] = fake_manager

        edit_after_publish = client.put(
            (
                "/api/v1/agent/knowledge/sources/"
                + source_id
            ),
            json={
                "title":
                    (
                        "Changed After Publish "
                        + unique_suffix
                    ),

                "type":
                    "POLICY",

                "version":
                    "1.0",

                "sections": [
                    {
                        "section":
                            "Forbidden",

                        "content":
                            "This must not be accepted.",
                    }
                ],
            },
        )

        assert (
            edit_after_publish.status_code
            == 409
        )


        # --------------------------------------------------
        # Retire published source.
        # --------------------------------------------------

        retired = client.post(
            (
                "/api/v1/agent/knowledge/sources/"
                + source_id
                + "/retire"
            ),
            json={
                "reason":
                    (
                        "Superseded by a newer "
                        "approved policy version."
                    )
            },
        )

        assert (
            retired.status_code
            == 200
        )

        retired_result = (
            retired.json()
        )

        assert (
            retired_result[
                "status"
            ]
            == "RETIRED"
        )

        assert (
            retired_result[
                "retired_at"
            ]
            is not None
        )


        # --------------------------------------------------
        # Agents lose access once retired.
        # --------------------------------------------------

        app.dependency_overrides[
            get_current_internal_user
        ] = fake_agent

        retired_as_agent = client.get(
            (
                "/api/v1/agent/knowledge/sources/"
                + source_id
            )
        )

        assert (
            retired_as_agent.status_code
            == 404
        )


        # --------------------------------------------------
        # Audit lifecycle.
        # --------------------------------------------------

        with psycopg.connect(
            settings.database_url
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    select event_type
                    from public.audit_events

                    where entity_type =
                        'knowledge_source'

                      and entity_id = %s

                    order by created_at;
                    """,
                    (
                        source_id,
                    ),
                )

                events = [
                    row[0]
                    for row
                    in cursor.fetchall()
                ]

        assert events == [
            "KNOWLEDGE_SOURCE_CREATED",
            "KNOWLEDGE_SOURCE_UPDATED",
            "KNOWLEDGE_SOURCE_PUBLISHED",
            "KNOWLEDGE_SOURCE_RETIRED",
        ]

    finally:
        app.dependency_overrides.clear()

        if source_id is not None:
            cleanup_source(
                source_id
            )