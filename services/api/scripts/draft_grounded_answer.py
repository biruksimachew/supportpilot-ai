import argparse

from app.services.embeddings import (
    get_embedding_provider,
)

from app.services.generation import (
    get_generation_provider,
)

from app.services.grounded_answer import (
    generate_grounded_answer,
)

from app.services.knowledge_retrieval import (
    retrieve_knowledge,
)


def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "question",
    )

    args = (
        parser.parse_args()
    )


    embedding_provider = (
        get_embedding_provider()
    )

    generation_provider = (
        get_generation_provider()
    )


    retrieval = retrieve_knowledge(
        question=
            args.question,

        provider=
            embedding_provider,

        top_k=
            5,

        min_similarity=
            0.0,
    )


    answer = generate_grounded_answer(
        question=
            args.question,

        retrieval=
            retrieval,

        provider=
            generation_provider,
    )


    print(
        f"Status: {answer.status}"
    )

    print(
        (
            "Generation: "
            f"{answer.generation_provider}"
            "/"
            f"{answer.generation_model}"
        )
    )

    print(
        (
            "Retrieval: "
            f"{answer.retrieval_provider}"
            "/"
            f"{answer.retrieval_model}"
        )
    )

    print()

    print(
        answer.answer
    )

    print()

    print(
        "Citations:"
    )


    for citation in answer.citations:
        print(
            (
                f"- [{citation.ref}] "
                f"{citation.title} "
                f"v{citation.version}"
                f" / {citation.section}"
                f" "
                f"({citation.similarity:.4f})"
            )
        )


    print()

    print(
        (
            "Generation time: "
            f"{answer.generation_ms} ms"
        )
    )


if __name__ == "__main__":
    main()