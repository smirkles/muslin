"""Anthropic SDK implementation of DiagnosisAgent.

Uses the direct anthropic Python SDK for single-shot message completions.
The DiagnosisAgent Protocol boundary in agent.py ensures this implementation
can be swapped for Managed Agents (Day 3) without touching HTTP callers.

Environment variables:
    ANTHROPIC_API_KEY: Required. Anthropic API key.
    ANTHROPIC_MODEL: Optional. Model ID override. Defaults to 'claude-opus-4-7'.
"""

import base64
import logging
import os
from pathlib import Path

import anthropic

from lib.diagnosis.agent import AgentResponse, ConfigError
from lib.diagnosis.prompts import load_prompt, substitute

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "claude-opus-4-7"


def _detect_media_type(image_bytes: bytes) -> str:
    """Detect the MIME type of image bytes from magic bytes.

    Returns 'image/png' for PNG files, 'image/jpeg' otherwise.
    """
    if image_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if image_bytes[:3] == b"GIF":
        return "image/gif"
    if image_bytes[:4] == b"RIFF" and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


class AnthropicAgent:
    """Concrete DiagnosisAgent that calls Claude via the Anthropic SDK.

    Reads ANTHROPIC_API_KEY from the environment at run() time so the key
    can be set after construction (e.g. in test fixtures). Raises ConfigError
    if the key is absent when run() is called.
    """

    def __init__(self, prompts_root: Path | None = None) -> None:
        """Initialise the agent.

        Args:
            prompts_root: Override the root prompts directory (used in tests).
        """
        self._prompts_root = prompts_root

    def run(
        self,
        prompt_name: str,
        variables: dict[str, str],
        images: list[bytes] | None = None,
        max_tokens: int = 256,
    ) -> AgentResponse:
        """Call Claude with the named prompt and return a structured response.

        Args:
            prompt_name: Name of the prompt directory under prompts/
                (e.g. 'hello_world').
            variables: Key/value pairs to substitute into the prompt template.
            images: Optional list of raw image bytes. Each is attached as a
                type:'image' content block (base64-encoded) before the text block.
            max_tokens: Maximum tokens to generate. Defaults to 256.

        Returns:
            AgentResponse with Claude's completion text and usage metadata.

        Raises:
            ConfigError: If ANTHROPIC_API_KEY is not set in the environment.
            FileNotFoundError: If the prompt file cannot be found.
            KeyError: If the prompt references a variable not supplied.
            anthropic.APIError: If the Anthropic SDK raises an API-level error.
        """
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ConfigError(
                "ANTHROPIC_API_KEY is not configured. "
                "Set ANTHROPIC_API_KEY in your environment or .env.local file."
            )

        # Load and render the prompt
        template = load_prompt(prompt_name, prompts_root=self._prompts_root)
        rendered_prompt = substitute(template, variables)

        # Build message content
        if images:
            # Attach image blocks before the text block
            content: str | list[dict] = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": _detect_media_type(img),
                        "data": base64.b64encode(img).decode(),
                    },
                }
                for img in images
            ] + [{"type": "text", "text": rendered_prompt}]
        else:
            # Text-only: keep original string form for backward compatibility
            content = rendered_prompt

        # Call the Anthropic API
        model = os.environ.get("ANTHROPIC_MODEL", _DEFAULT_MODEL)
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": content}],
        )

        logger.info(
            "Claude response: model=%s input_tokens=%d output_tokens=%d",
            model,
            message.usage.input_tokens,
            message.usage.output_tokens,
        )

        return AgentResponse(
            text=message.content[0].text,
            model=model,
            input_tokens=message.usage.input_tokens,
            output_tokens=message.usage.output_tokens,
        )
