from enum import Enum

class DataType(Enum):
    NON_REPLICATED = 1
    REPLICATED = 2

class Action(Enum):
    BEGIN = 1
    BEGIN_RO = 2
    READ = 3
    WRITE = 4
    DUMP = 5
    END = 6
    FAIL = 7
    RECOVER = 8

class TransactionStatus(Enum):
    ACTIVE = 1
    WAITING = 2
    COMMITTED = 3
    ABORTED = 4
    ABORTING = 5
