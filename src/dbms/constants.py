from enum import Enum

class DataType(Enum):
    NON_REPLICATED = 1
    REPLICATED = 2

class Action(Enum):
    BEGIN = 1
    BEGIN_RO = 2
    WRITE = 3
    READ = 4
    FAIL = 5
    END = 6
    RECOVER = 7
    DUMP = 8
