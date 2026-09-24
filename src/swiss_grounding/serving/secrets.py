"""The shared keys (Supertext translation, zbern.ch token), distributed as an asset of the private release.

The team publishes `supertext.env` next to the corpus dump; `setup` downloads it with the caller's
GitHub login and writes its keys into `.env`. Only the keys listed here are ever taken from the
asset, so a stray line cannot change any other setting. Pure functions; the CLI does the I/O.
"""
import re
from collections.abc import Mapping

SECRETS_ASSET = "supertext.env"
SHARED_KEYS: tuple[str, ...] = ("SUPERTEXT_API_KEY", "ZBERN_MCP_TOKEN")
HEADER = "# Shared keys installed by `swiss-grounding setup`"
LINE = re.compile(r"^\s*#?\s*([A-Z][A-Z0-9_]*)\s*=\s*(.*?)\s*$")


def parse_env(text: str) -> dict[str, str]:
    """KEY=VALUE lines of a dotenv text, restricted to the shared keys; comments and blanks ignored."""
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = LINE.match(line)
        if m and m.group(1) in SHARED_KEYS and m.group(2):
            out[m.group(1)] = m.group(2).strip("'\"")
    return out


def shared_env_text(values: Mapping[str, str]) -> str:
    """The asset's content: one line per shared key that has a value."""
    return "".join(f"{k}={values[k]}\n" for k in SHARED_KEYS if values.get(k))


def merge_env(env_text: str, shared: Mapping[str, str]) -> str:
    """`env_text` with each shared key set to its value.

    A line already holding the key, live or commented out, is replaced where it stands so the
    file keeps its shape; a key the file does not mention is appended under a header. Keys outside
    SHARED_KEYS are ignored."""
    wanted = {k: v for k, v in shared.items() if k in SHARED_KEYS and v}
    if not wanted:
        return env_text
    lines = env_text.splitlines()
    done: set[str] = set()
    out: list[str] = []
    for line in lines:
        m = LINE.match(line)
        key = m.group(1) if m else None
        if key in wanted and key not in done:
            out.append(f"{key}={wanted[key]}")
            done.add(key)
        else:
            out.append(line)
    missing = [k for k in SHARED_KEYS if k in wanted and k not in done]
    if missing:
        if out and out[-1].strip():
            out.append("")
        out.append(HEADER)
        out.extend(f"{k}={wanted[k]}" for k in missing)
    return "\n".join(out) + "\n"
