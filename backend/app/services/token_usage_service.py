def estimate_tokens(text: str) -> int:
    if not text:
        return 0

    return max(1, round(len(text) / 4))


def estimate_chat_tokens(messages: list[dict]) -> int:
    total = 0

    for message in messages:
        total += estimate_tokens(message.get("content", ""))

    return total


def estimate_ai_usage_tokens(
    question: str,
    context: str,
    answer: str = "",
):
    return estimate_tokens(question) + estimate_tokens(context) + estimate_tokens(answer)
