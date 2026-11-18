import os
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type, retry_if_exception
from openai import RateLimitError, BadRequestError
from configs.logger import get_logger

logger = get_logger(__name__)


def _log_retry(retry_state):
    reason = retry_state.outcome.exception() if retry_state.outcome else None
    kind = ("Model output could not be parsed (tool_use_failed / output_parse_failed)"
            if isinstance(reason, BadRequestError) else "Rate limited by Groq API")
    logger.warning(
        f"{kind}. Retrying in {retry_state.next_action.sleep}s "
        f"(Attempt {retry_state.attempt_number}/7)..."
    )


def _is_transient_tool_call_error(exception: BaseException) -> bool:
    """Rate limits are always worth retrying. So is this specific, observed-live failure
    mode: some models occasionally answer by inventing a bogus tool call and stuffing
    free-form text where structured arguments belong, which the server-side parser rejects
    with a 400 'tool_use_failed'. That's a non-deterministic sampling issue, not a
    permanently malformed request -- a retry can just succeed. Any OTHER BadRequestError
    (a genuinely malformed prompt, bad params, etc.) is NOT retried, since retrying an
    actually-invalid request would just fail identically every time.

    It happens with and without tools: openai/gpt-oss-20b was trained with built-in tools
    and, even on a plain chat call with no tools at all, sometimes emits one (observed live:
    'repo_browser.print_tree' from the testing agent -> "Tool choice is none, but model
    called a tool"). So every agent needs this, not only the tool-calling ones.
    """
    if isinstance(exception, RateLimitError):
        return True
    if isinstance(exception, BadRequestError):
        # 'output_parse_failed': same family -- the model put its reasoning where the final
        # answer belongs and Groq's parser rejected it (seen live in the security agent).
        text = str(exception)
        return "tool_use_failed" in text or "output_parse_failed" in text
    return False


# Plain chat agents: retry rate limits AND spurious tool calls (see above).
llm_retry = retry(
    retry=retry_if_exception(_is_transient_tool_call_error),
    wait=wait_exponential(multiplier=2, min=5, max=120),
    stop=stop_after_attempt(7),
    before_sleep=_log_retry
)


# Tool-calling agents (create_react_agent): same policy.
llm_retry_tool_calling = retry(
    retry=retry_if_exception(_is_transient_tool_call_error),
    wait=wait_exponential(multiplier=2, min=5, max=120),
    stop=stop_after_attempt(7),
    before_sleep=_log_retry
)
