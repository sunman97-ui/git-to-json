from rich.console import Console
from typing import List
from src.schemas import PromptTemplate, CommitData
from src.utils import count_tokens


def build_prompt(
    console: Console,
    template: PromptTemplate,
    data: List[CommitData],
    max_tokens: int = 120000,
) -> str:
    if not data:
        return ""

    # Start with the token count of the template's boilerplate
    base_prompt = f"--- SYSTEM PROMPT ---\n{template.prompts.system}\n\n--- USER PROMPT ---\n{template.prompts.user}"  # noqa: E501

    current_tokens = count_tokens(base_prompt.replace("{DIFF_CONTENT}", ""))

    chunks = []
    omitted_commits = 0

    for commit in data:
        commit_chunk = f"--- Diff for {commit.short_hash}: {commit.message.splitlines()[0]} ---\n{commit.diff}"  # noqa: E501
        commit_tokens = count_tokens(commit_chunk)

        if current_tokens + commit_tokens > max_tokens:
            omitted_commits = len(data) - len(chunks)
            break

        chunks.append(commit_chunk)
        current_tokens += commit_tokens

    raw_diff = "\n\n".join(chunks)

    if omitted_commits > 0:
        truncation_message = f"\n\n[INFO: {omitted_commits} commits were omitted to fit within the token limit.]"  # noqa: E501
        raw_diff += truncation_message

    final_user_prompt = template.prompts.user.replace("{DIFF_CONTENT}", raw_diff)

    full_payload = (
        f"--- SYSTEM PROMPT ---\n{template.prompts.system}\n\n"
        f"--- USER PROMPT ---\n{final_user_prompt}"
    )

    final_token_count = count_tokens(full_payload)
    console.print(
        f"   📊  Payload size: ~{final_token_count} tokens (max {max_tokens})",
        style="dim",
    )

    return full_payload
