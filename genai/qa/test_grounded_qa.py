
from genai.qa.grounded_qa import (
    GroundedQA,
    display_response,
)


def main():

    qa = GroundedQA(top_k=5)

    test_questions = [
        {
            "id": "T001",
            "question": (
                "What are the safety rules for forklift operators?"
            ),
        },
        {
            "id": "T002",
            "question": (
                "How should warehouse PPE be selected and maintained?"
            ),
        },
        {
            "id": "T003",
            "question": (
                "What should workers do during an emergency evacuation?"
            ),
        },
        {
            "id": "T004",
            "question": (
                "What was the exact temperature in Warehouse 17 yesterday?"
            ),
        },
    ]

    for test in test_questions:

        print("\n\n")
        print("#" * 70)
        print("TEST:", test["id"])
        print("#" * 70)

        try:

            response = qa.ask(
                test["question"]
            )

            display_response(response)

        except Exception as error:

            print("TEST FAILED:", error)


if __name__ == "__main__":
    main()

