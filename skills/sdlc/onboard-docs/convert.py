"""MarkItDown wrapper for VSAF SDLC onboard-docs.

Converts documents to Markdown using MarkItDown Python API.
Reads config from ~/.vsaf/markitdown.env for OCR settings.
Runs inside markitdown's pipx venv (all deps pre-installed).

Supported LLM providers for OCR:
  - OpenAI (native)
  - Google Gemini (via OpenAI-compatible endpoint)
  - Anthropic Claude (via built-in adapter)
  - Any OpenAI-compatible provider (via custom base_url)

Exit codes:
  0 — success (content extracted and written)
  1 — input file not found
  2 — conversion error (markitdown exception)
  3 — empty content (markitdown returned nothing)

Usage:
  python convert.py --input file.pdf --output output.md [--config path]
"""

import argparse
import os
import sys
from pathlib import Path


# ── Anthropic Adapter ──
# markitdown-ocr calls client.chat.completions.create() and reads
# response.choices[0].message.content. Anthropic SDK uses a different
# interface, so this adapter bridges the two.


class _Choice:
    def __init__(self, text: str):
        self.message = type("Msg", (), {"content": text})()


class _Response:
    def __init__(self, text: str):
        self.choices = [_Choice(text)]


class AnthropicAdapter:
    """Wraps anthropic SDK to match OpenAI chat.completions.create() interface."""

    def __init__(self, api_key: str):
        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key)
        self.chat = self
        self.completions = self

    def create(self, *, model, messages, **_kwargs):
        anthropic_messages = []
        for msg in messages:
            content_blocks = []
            for part in msg["content"]:
                if part["type"] == "text":
                    content_blocks.append({"type": "text", "text": part["text"]})
                elif part["type"] == "image_url":
                    data_uri = part["image_url"]["url"]
                    # data:image/png;base64,xxxx → extract media_type + base64
                    header, b64_data = data_uri.split(",", 1)
                    media_type = header.split(":")[1].split(";")[0]
                    content_blocks.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": b64_data,
                        },
                    })
            anthropic_messages.append({"role": msg["role"], "content": content_blocks})

        response = self._client.messages.create(
            model=model,
            max_tokens=4096,
            messages=anthropic_messages,
        )
        text = response.content[0].text if response.content else ""
        return _Response(text)


# ── Client Factory ──


def _detect_provider(base_url: str) -> str:
    """Detect provider name from base_url for logging."""
    if "anthropic.com" in base_url:
        return "Claude"
    if "googleapis.com" in base_url:
        return "Gemini"
    if "openai.com" in base_url:
        return "OpenAI"
    if "openrouter.ai" in base_url:
        return "OpenRouter"
    return "Custom"


def create_llm_client(api_key: str, base_url: str):
    """Create LLM client based on base_url."""
    if "anthropic.com" in base_url:
        return AnthropicAdapter(api_key=api_key)
    else:
        from openai import OpenAI

        return OpenAI(api_key=api_key, base_url=base_url)


# ── Config ──


def load_env(config_path: str) -> dict[str, str]:
    """Parse a .env file into a dict. Shell env vars take priority."""
    values: dict[str, str] = {}

    path = Path(config_path).expanduser()
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("\"'")
            values[key] = value

    # Shell env vars override file values
    for key in ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL", "OPENAI_API_KEY", "MARKITDOWN_MODEL"):
        env_val = os.environ.get(key)
        if env_val:
            values[key] = env_val

    return values


# ── Main ──


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert documents to Markdown via MarkItDown")
    parser.add_argument("--input", required=True, help="Input file to convert")
    parser.add_argument("--output", required=True, help="Output markdown file")
    parser.add_argument(
        "--config",
        default=str(Path.home() / ".vsaf" / "markitdown.env"),
        help="Path to markitdown config file (default: ~/.vsaf/markitdown.env)",
    )
    args = parser.parse_args()

    # Validate input
    if not Path(args.input).is_file():
        print(f"[convert] Error: input file not found: {args.input}", file=sys.stderr)
        return 1

    # Load config with backward compat
    config = load_env(args.config)
    api_key = config.get("LLM_API_KEY") or config.get("OPENAI_API_KEY") or ""
    model = config.get("LLM_MODEL") or config.get("MARKITDOWN_MODEL") or "gpt-4o"
    base_url = config.get("LLM_BASE_URL") or "https://api.openai.com/v1"

    # Initialize MarkItDown
    from markitdown import MarkItDown

    if api_key:
        client = create_llm_client(api_key, base_url)
        provider = _detect_provider(base_url)
        md = MarkItDown(enable_plugins=True, llm_client=client, llm_model=model)
        print(f"[convert] OCR enabled (model: {model}, provider: {provider})")
    else:
        md = MarkItDown()
        print("[convert] OCR disabled (no LLM_API_KEY)")

    # Convert
    try:
        result = md.convert(args.input)
    except Exception as exc:
        print(f"[convert] Error converting {args.input}: {exc}", file=sys.stderr)
        return 2

    # Write output
    content = result.text_content or ""
    if not content:
        print(f"[convert] Warning: no content extracted from {args.input}", file=sys.stderr)
        return 3

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")
    print(f"[convert] {args.input} → {args.output} ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
