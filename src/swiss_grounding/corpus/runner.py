from dataclasses import dataclass


@dataclass(frozen=True)
class LlmTask:
    custom_id: str
    model: str
    system: str
    user: str
    image_png_b64: str | None = None
    max_output_tokens: int = 800


@dataclass(frozen=True)
class LlmOutcome:
    custom_id: str
    data: dict | None
    input_tokens: int
    output_tokens: int
    error: str | None = None
