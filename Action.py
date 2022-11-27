from enum import Enum

class Action(Enum):
    BEGIN = 1
    BEGIN_RO = 2
    WRITE = 3
    READ = 4
    FAIL = 5
    END = 6
    RECOVER = 7
    DUMP = 8