from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type
from openai import RateLimitError
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
