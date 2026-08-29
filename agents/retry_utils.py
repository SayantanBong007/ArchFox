import os
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type, retry_if_exception
from openai import RateLimitError, BadRequestError
from configs.logger import get_logger

logger = get_logger(__name__)


def _log_retry(retry_state):
    logger.warning(
        f"Rate limited by Groq API. Retrying in {retry_state.next_action.sleep}s "
        f"(Attempt {retry_state.attempt_number}/7)..."
    )


llm_retry = retry(
    retry=retry_if_exception_type(RateLimitError),
    wait=wait_exponential(multiplier=2, min=5, max=120),
    stop=stop_after_attempt(7),
    before_sleep=_log_retry
)


def _is_transient_tool_call_error(exception: BaseException) -> bool:
    """Rate limits are always worth retrying. So is this specific, observed-live failure
    mode: some models occasionally answer through create_react_agent by inventing a bogus
    tool call and stuffing free-form text where structured arguments belong, which OpenAI's
    server-side parser rejects with a 400 'tool_use_failed'. That's a non-deterministic
    sampling issue, not a permanently malformed request -- a retry can just succeed. Any
    OTHER BadRequestError (a genuinely malformed prompt, bad params, etc.) is NOT retried,
    since retrying an actually-invalid request would just fail identically every time.
    """
    if isinstance(exception, RateLimitError):
        return True
    if isinstance(exception, BadRequestError):
        return "tool_use_failed" in str(exception)
    return False


llm_retry_tool_calling = retry(
    retry=retry_if_exception(_is_transient_tool_call_error),
    wait=wait_exponential(multiplier=2, min=5, max=120),
    stop=stop_after_attempt(7),
    before_sleep=_log_retry
)
