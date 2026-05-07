"""dexter.utils package."""

from .env import get_env, has_env, load_env
from .errors import (
    classify_error,
    format_user_facing_error,
    is_context_overflow_error,
    is_non_retryable_error,
)
from .format import format_tool_result, truncate
from .logger import logger
from .paths import (
    cache_dir,
    dexter_path,
    dexter_root,
    scratchpad_dir,
    settings_path,
)
from .tokens import estimate_tokens, get_auto_compact_threshold

__all__ = [
    "load_env",
    "get_env",
    "has_env",
    "logger",
    "dexter_root",
    "dexter_path",
    "scratchpad_dir",
    "cache_dir",
    "settings_path",
    "estimate_tokens",
    "get_auto_compact_threshold",
    "classify_error",
    "is_non_retryable_error",
    "is_context_overflow_error",
    "format_user_facing_error",
    "format_tool_result",
    "truncate",
]
