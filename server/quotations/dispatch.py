"""
Unified background task dispatch helper for QuoteFlow AI.
Ensures background processing tasks run in isolated daemon threads with dedicated database connections,
providing consistent, asynchronous execution across both local environments (no Redis) and production.
"""

import logging
import threading
from typing import Callable, Any
from django.db import connection

logger = logging.getLogger('quoteflow.dispatch')


def dispatch_background_task(target_fn: Callable, *args: Any, **kwargs: Any) -> threading.Thread:
    """
    Executes target_fn in a daemon thread, isolating database connection state.
    Closes the connection before and after task execution to prevent connection leaks
    and SQLite thread-affinity locking.
    When CELERY_TASK_ALWAYS_EAGER is True (such as during test execution), runs synchronously
    to prevent SQLite database table lock contention.
    """
    from django.conf import settings

    # Run inline ONLY under the test runner. Do NOT key this off CELERY_TASK_ALWAYS_EAGER:
    # production sets eager=True (no broker), and running inline there blocks the HTTP request.
    if getattr(settings, 'BACKGROUND_TASKS_SYNC', False):
        try:
            target_fn(*args, **kwargs)
        except Exception as exc:
            logger.error("Eager background task %s execution failed: %s", getattr(target_fn, '__name__', str(target_fn)), exc)
        return None

    fn_name = getattr(target_fn, '__name__', str(target_fn))

    def _worker():
        connection.close()
        try:
            target_fn(*args, **kwargs)
        except Exception as exc:
            logger.error("Background task %s execution failed: %s", fn_name, exc, exc_info=True)
        finally:
            connection.close()

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    logger.info("Dispatched background task %s in daemon thread %s", fn_name, thread.name)
    return thread
