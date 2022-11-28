from enum import Enum

class TransactionStatus(Enum):
    ACTIVE = 1
    WAITING = 2
    COMMITTED = 3
    ABORTED = 4
    SHOULD_ABORTED = 5

class Transaction:
    def __init__(self, beginTime: int, id: int) -> None:
        self.beginTime = beginTime
        self.id = id
        self.status = TransactionStatus.ACTIVE
        self.isReadyOnly = False
        self.data = dict()
