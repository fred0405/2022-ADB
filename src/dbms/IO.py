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
        ret = ''
        ret += f'Timestamp: {self.timeStamp} \n'
        ret += f'Action: {self.action} \n'
        ret += f'Trx ID: {self.trxID} \n'
        ret += f'Var ID: {self.varID} \n'
        ret += f'Site ID: {self.siteID} \n'
        ret += f'Write value: {self.writesToVal} \n'
        return ret

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

    # def parseFile(self):
    #     f = open(self.inputFile, 'r')
    #     fileline = f.readline()
    #     while fileline:
    #         file_line = fileline.strip()
    #         fileline = f.readline()
    #         if len(file_line) == 0 or file_line.startswith('/') or file_line.startswith('//'):
    #             continue
    #         parts = re.split('\(|\)|,', file_line)
    #         action = parts[0]
    #         operation = Operation()
    #         if action == 'begin':
    #             operation.action = Action.BEGIN
    #             operation.trxID = self.getNum(parts[1])
    #         elif action == "beginRO":
    #             operation.action = Action.BEGIN_RO
    #             operation.trxID = self.getNum(parts[1])
                
    #         elif action == "end":
    #             operation.action = Action.END
    #             operation.trxID = self.getNum(parts[1])
                
    #         elif action == "W":
    #             operation.action = Action.WRITE
    #             operation.trxID = self.getNum(parts[1])
    #             operation.varID = self.getNum(parts[2])
    #             operation.writesToVal = self.getNum(parts[3])
                
    #         elif action == "R":
    #             operation.action = Action.READ
    #             operation.trxID = self.getNum(parts[1])
    #             operation.varID = self.getNum(parts[2])
                
    #         elif action == "fail":
    #             operation.action = Action.FAIL
    #             operation.siteID = self.getNum(parts[1])
                
    #         elif action == "recover":
    #             operation.action = Action.RECOVER
    #             operation.siteID = self.getNum(parts[1])
                
    #         elif action == "dump":
    #             operation.action = Action.DUMP
    #         self.operations.append(operation)
    #         self.currentTime += 1
    #     f.close()

    def getNum(self, s):
        for i in range(len(s)):
            if not s[i].isdigit():
                continue
            return int(s[i:])
        return -1
