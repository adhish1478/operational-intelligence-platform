import time
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerOpenException(Exception):
    """Raised when an operation is blocked because the Circuit Breaker is OPEN."""
    pass


class CircuitBreaker:
    """
    Stateful Circuit Breaker pattern implementation.
    
    States:
    - CLOSED: Normal operation. All calls allowed.
    - OPEN: Service tripped after failure threshold exceeded. Calls blocked.
    - HALF_OPEN: Cooldown period elapsed. Allowing trial calls to test service recovery.
    """

    def __init__(self, failure_threshold: int = 5, reset_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_state_change = time.time()
        self.last_failure_time = 0.0

    def allow_request(self) -> bool:
        """Determines whether a message/request is allowed to proceed."""
        now = time.time()
        
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if cooldown reset timeout has elapsed
            if now - self.last_state_change >= self.reset_timeout:
                logger.info("CircuitBreaker reset timeout elapsed. Transitioning from OPEN -> HALF_OPEN.")
                self.state = CircuitState.HALF_OPEN
                self.last_state_change = now
                return True
            return False

        if self.state == CircuitState.HALF_OPEN:
            return True

        return True

    def record_success(self):
        """Records a successful execution, resetting circuit breaker to CLOSED."""
        if self.state in (CircuitState.HALF_OPEN, CircuitState.OPEN):
            logger.info(f"CircuitBreaker operation succeeded. Transitioning from {self.state.value} -> CLOSED.")
        
        self.failure_count = 0
        self.state = CircuitState.CLOSED
        self.last_state_change = time.time()

    def record_failure(self):
        """Records an execution failure and trips circuit breaker if threshold reached."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.state == CircuitState.HALF_OPEN:
            logger.warning("CircuitBreaker operation failed while in HALF_OPEN. Transitioning -> OPEN.")
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()
        elif self.failure_count >= self.failure_threshold and self.state == CircuitState.CLOSED:
            logger.error(
                f"CircuitBreaker reached failure threshold ({self.failure_count}/{self.failure_threshold}). "
                f"Tripping circuit -> OPEN for {self.reset_timeout}s."
            )
            self.state = CircuitState.OPEN
            self.last_state_change = time.time()

    def get_stats(self) -> dict:
        """Returns circuit breaker state diagnostic metrics."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "failure_threshold": self.failure_threshold,
            "reset_timeout": self.reset_timeout,
            "last_state_change": self.last_state_change,
            "seconds_since_state_change": round(time.time() - self.last_state_change, 2),
        }
