from rich.console import Console
from typing import List
from src.schemas import PromptTemplate, CommitData
from src.utils import count_tokens


def build_prompt(
    console: Console, template: PromptTemplate, data: List[CommitData]
) -> str:
    if not data:
        return ""

    if len(data) == 1:
        raw_diff = data[0].diff
    else:
        # Optimized concatenation
        combined_diffs = [
            f"--- Diff for {c.short_hash}: {c.message.splitlines()[0]} ---\n{c.diff}"
            for c in data
        ]
        raw_diff = "\n\n".join(combined_diffs)

    final_user_prompt = template.prompts.user.replace("{DIFF_CONTENT}", raw_diff)

    # RE-ADDED HEADERS to match test expectations and improve LLM clarity
    full_payload = (
        f"--- SYSTEM PROMPT ---\n{template.prompts.system}\n\n"
        f"--- USER PROMPT ---\n{final_user_prompt}"
    )

    token_count = count_tokens(full_payload)
    console.print(f"   📊  Payload size: ~{token_count} tokens", style="dim")

    return full_payload
