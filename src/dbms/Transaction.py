from .constants import TransactionStatus

class Transaction:
    def __init__(self, beginTime: int, id: int) -> None:
        self.beginTime = beginTime
        self.id = id
        self.status = TransactionStatus.ACTIVE
        self.isReadyOnly = False
        self.data = dict()
