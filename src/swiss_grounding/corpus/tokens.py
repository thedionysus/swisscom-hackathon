"""Token counts for the Batch API's enqueued-token limit.

The budget keeps its conservative characters / 3 estimate (budget.estimate_tokens) so the cap errs on the
safe side. Splitting Batch files needs the real count instead: measured on chunk prompts, characters / 3
overstated tokens by about 45%, which left every file a third empty against the queue limit.
"""
from functools import cache

import tiktoken

ENCODING = "o200k_base"     # the gpt-5 family's tokenizer


@cache
def _encoding() -> tiktoken.Encoding:
    return tiktoken.get_encoding(ENCODING)


def count_tokens(text: str) -> int:
    return len(_encoding().encode(text, disallowed_special=()))
