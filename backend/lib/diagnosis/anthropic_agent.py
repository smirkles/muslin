"""Anthropic SDK implementation of DiagnosisAgent.

Uses the direct anthropic Python SDK for single-shot message completions.
The DiagnosisAgent Protocol boundary in agent.py ensures this implementation
can be swapped for Managed Agents (Day 3) without touching HTTP callers.

Environment variables:
    ANTHROPIC_API_KEY: Required. Anthropic API key.
    ANTHROPIC_MODEL: Optional. Model ID override. Defaults to 'claude-opus-4-7'.
"""

import logging
import os
from pathlib import Path

import anthropic

from lib.diagnosis.agent import AgentResponse, ConfigError
from lib.diagnosis.prompts import load_prompt, substitute

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "claude-opus-4-7"


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

    def run(self, prompt_name: str, variables: dict[str, str]) -> AgentResponse:
        """Call Claude with the named prompt and return a structured response.

        Args:
            prompt_name: Name of the prompt directory under prompts/
                (e.g. 'hello_world').
            variables: Key/value pairs to substitute into the prompt template.

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

        # Call the Anthropic API
        model = os.environ.get("ANTHROPIC_MODEL", _DEFAULT_MODEL)
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=model,
            max_tokens=256,
            messages=[{"role": "user", "content": rendered_prompt}],
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
