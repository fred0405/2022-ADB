from collections import deque
import re

from .constants import Action

class Operation:
    def __init__(self) -> None:
        self.timeStamp = None
        self.action = None
        self.trxID = None
        self.varID = None
        self.siteID = None
        self.writesToVal = None

    def __repr__(self) -> str:
        ret = '('
        ret += f'Time:{self.timeStamp} {self.action}'
        if self.trxID is not None:
            ret += f' Txn:{self.trxID}'
        if self.varID is not None:
            ret += f' Var:{self.varID}'
        if self.siteID is not None:
            ret += f' Site:{self.siteID}'
        if self.writesToVal is not None:
            ret += f' Write_val:{self.writesToVal}'
        return ret + ')'

class IO:
    def __init__(self) -> None:
        self.inputFile = ''
        self.currentTime = 0
        self.operations = deque()

    def parse_line(self) -> Operation:
        line = input()
        # remove comments
        line = line.split('//')[0]
        if not line or not line.strip():
            return None
        tokens = re.split('\(|\)|,', line)
        tokens = [t.strip() for t in tokens if t.strip()]
        action = tokens[0]
        op = Operation()
        op.timeStamp = self.currentTime
        if action == 'begin':
            op.action = Action.BEGIN
            op.trxID = self.getNum(tokens[1])
        elif action == "beginRO":
            op.action = Action.BEGIN_RO
            op.trxID = self.getNum(tokens[1])
        elif action == "end":
            op.action = Action.END
            op.trxID = self.getNum(tokens[1])
        elif action == "W":
            op.action = Action.WRITE
            op.trxID = self.getNum(tokens[1])
            op.varID = self.getNum(tokens[2])
            op.writesToVal = self.getNum(tokens[3])
        elif action == "R":
            op.action = Action.READ
            op.trxID = self.getNum(tokens[1])
            op.varID = self.getNum(tokens[2])
        elif action == "fail":
            op.action = Action.FAIL
            op.siteID = self.getNum(tokens[1])
        elif action == "recover":
            op.action = Action.RECOVER
            op.siteID = self.getNum(tokens[1])
        elif action == "dump":
            op.action = Action.DUMP
        self.currentTime += 1
        return op

    def getNum(self, s):
        for i in range(len(s)):
            if not s[i].isdigit():
                continue
            return int(s[i:])
        return -1
