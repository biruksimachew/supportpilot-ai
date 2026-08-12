import argparse

from app.services.embeddings import (
    get_embedding_provider,
)

from app.services.knowledge_retrieval import (
    retrieve_knowledge,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Search SupportPilot approved "
            "knowledge semantically."
        )
    )

    parser.add_argument(
        "question",
    )

    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
    )

    parser.add_argument(
        "--min-similarity",
        type=float,
        default=0.0,
    )


    args = (
        parser.parse_args()
    )


    provider = (
        get_embedding_provider()
    )


    result = retrieve_knowledge(
        question=
            args.question,

        provider=
            provider,

        top_k=
            args.top_k,

        min_similarity=
            args.min_similarity,
    )


    print(
        "SupportPilot semantic retrieval"
    )

    print(
        (
            "Provider: "
            f"{result.provider}"
        )
    )

    print(
        (
            "Model: "
            f"{result.model}"
        )
    )

    print(
        (
            "Question: "
            f"{result.question}"
        )
    )

    print(
        (
            "Results: "
            f"{len(result.results)}"
        )
    )


    for index, item in enumerate(
        result.results,
        start=1,
    ):
        print()

        print(
            (
                f"{index}. "
                f"{item.title} "
                f"v{item.version}"
            )
        )

        print(
            (
                "   Section: "
                f"{item.section}"
            )
        )

        print(
            (
                "   Similarity: "
                f"{item.similarity:.4f}"
            )
        )

        preview = (
            item.content
            .replace(
                "\n",
                " ",
            )
            .strip()
        )

        if len(preview) > 180:
            preview = (
                preview[:177]
                + "..."
            )

        print(
            (
                "   Evidence: "
                f"{preview}"
            )
        )


if __name__ == "__main__":
    main()