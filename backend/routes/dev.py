"""Dev-only routes — NOT for production use.

These endpoints exist solely to validate the project scaffold and support
local development. They are registered under the /dev prefix and must not
be exposed in user-facing API documentation.
"""

import logging

import anthropic
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from lib.diagnosis.agent import ConfigError
from lib.diagnosis.anthropic_agent import AnthropicAgent
from lib.utils import reverse_string

logger = logging.getLogger(__name__)

# DEV-ONLY: This router is intended for local development and testing only.
router = APIRouter(prefix="/dev", tags=["dev"])


class ReverseStringRequest(BaseModel):
    """Request body for POST /dev/reverse-string."""

    model_config = ConfigDict(strict=True)

    input: str


class ReverseStringResponse(BaseModel):
    """Response body for POST /dev/reverse-string."""

    result: str


@router.post("/reverse-string", response_model=ReverseStringResponse)
def post_reverse_string(body: ReverseStringRequest) -> ReverseStringResponse:
    """Reverse the input string and return it.

    This is a dev/test endpoint — do not use in production.
    """
    return ReverseStringResponse(result=reverse_string(body.input))


# ---------------------------------------------------------------------------
# POST /dev/hello-agent
# ---------------------------------------------------------------------------


class HelloAgentRequest(BaseModel):
    """Request body for POST /dev/hello-agent."""

    model_config = ConfigDict(strict=True)

    name: str = Field(..., min_length=1, max_length=100)


class HelloAgentResponse(BaseModel):
    """Response body for POST /dev/hello-agent."""

    text: str
    model: str
    input_tokens: int
    output_tokens: int


def get_agent() -> AnthropicAgent:
    """Return the AnthropicAgent instance used by this route.

    Extracted into a function so tests can patch it cleanly.
    """
    return AnthropicAgent()


@router.post("/hello-agent", response_model=HelloAgentResponse)
def post_hello_agent(body: HelloAgentRequest) -> HelloAgentResponse:
    """Call Claude and return a greeting for the supplied name.

    DEV-ONLY: Validates end-to-end Anthropic API wiring. Do not use in production.

    Errors:
        422 — name is empty or longer than 100 characters (FastAPI validation).
        500 — ANTHROPIC_API_KEY is missing from the environment.
        502 — The Anthropic SDK raised an API-level error (network, auth, rate limit).
    """
    agent = get_agent()
    try:
        response = agent.run("hello_world", {"name": body.name})
    except ConfigError as exc:
        logger.warning("ANTHROPIC_API_KEY not configured: %s", exc)
        raise HTTPException(status_code=500, detail="ANTHROPIC_API_KEY not configured") from exc
    except anthropic.APIError as exc:
        logger.exception("Anthropic API error calling /dev/hello-agent: %s", exc)
        raise HTTPException(status_code=502, detail="Claude API error") from exc

    return HelloAgentResponse(
        text=response.text,
        model=response.model,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
    )
