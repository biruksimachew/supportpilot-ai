from psycopg.rows import dict_row

from app.core.database import (
    get_database_connection,
)

from app.schemas.auth import (
    InternalUser,
)

from app.services.embeddings import (
    get_embedding_provider,
)

from app.services.knowledge_index import (
    index_knowledge_source,
)


def load_manager() -> InternalUser:
    with get_database_connection() as connection:
        connection.row_factory = dict_row

        with connection.cursor() as cursor:
            cursor.execute(
                """
                select
                    id,
                    email,
                    name,
                    role

                from public.users

                where status = 'ACTIVE'
                  and role in (
                      'SUPPORT_MANAGER',
                      'SYSTEM_ADMIN'
                  )

                order by
                    case role
                        when 'SUPPORT_MANAGER'
                            then 1
                        else 2
                    end

                limit 1;
                """
            )

            row = cursor.fetchone()


    if row is None:
        raise RuntimeError(
            (
                "No active manager or administrator "
                "exists. Run staff bootstrap first."
            )
        )


    return InternalUser(
        **row
    )


def load_published_source_ids():
    with get_database_connection() as connection:
        connection.row_factory = dict_row

        with connection.cursor() as cursor:
            cursor.execute(
                """
                select id, title, version

                from public.knowledge_sources

                where status = 'PUBLISHED'

                order by
                    title,
                    version,
                    id;
                """
            )

            return cursor.fetchall()


def main() -> None:
    user = load_manager()

    provider = (
        get_embedding_provider()
    )

    sources = (
        load_published_source_ids()
    )


    print(
        "SupportPilot knowledge indexing"
    )

    print(
        (
            "Provider: "
            f"{provider.provider_name}"
        )
    )

    print(
        (
            "Model: "
            f"{provider.model}"
        )
    )

    print(
        (
            "Dimensions: "
            f"{provider.dimensions}"
        )
    )

    print(
        (
            "Published sources: "
            f"{len(sources)}"
        )
    )


    total_embedded = 0
    total_skipped = 0


    for source in sources:
        result = (
            index_knowledge_source(
                user=user,

                source_id=
                    source["id"],

                provider=provider,
            )
        )

        total_embedded += (
            result.embedded_chunks
        )

        total_skipped += (
            result.skipped_chunks
        )

        print(
            (
                f"READY {source['title']} "
                f"v{source['version']} "
                f"embedded="
                f"{result.embedded_chunks} "
                f"skipped="
                f"{result.skipped_chunks}"
            )
        )


    print(
        (
            "Completed: "
            f"embedded={total_embedded}, "
            f"skipped={total_skipped}"
        )
    )


if __name__ == "__main__":
    main()