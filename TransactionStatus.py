from enum import Enum

class TransactionStatus(Enum):
    ACTIVE = 1
    WAITING = 2
    COMMITTED = 3
    ABORTED = 4
    SHOULD_ABORTED = 5