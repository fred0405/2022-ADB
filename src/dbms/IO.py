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
    def __init__(self, inputFile) -> None:
        self.inputFile = inputFile
        self.currentTime = 0
        self.operations = deque()

    def parseFile(self):
        f = open(self.inputFile, 'r')
        fileline = f.readline()
        while fileline:
            file_line = fileline.strip()
            fileline = f.readline()
            if len(file_line) == 0 or file_line.startswith('/') or file_line.startswith('//'):
                continue
            parts = re.split('\\(|\\)|,', file_line)
            action = parts[0]
            operation = Operation()
            if action == 'begin':
                operation.action = Action.BEGIN
                operation.trxID = self.getNum(parts[1])
            elif action == "beginRO":
                operation.action = Action.BEGIN_RO
                operation.trxID = self.getNum(parts[1])
                
            elif action == "end":
                operation.action = Action.END
                operation.trxID = self.getNum(parts[1])
                
            elif action == "W":
                operation.action = Action.WRITE
                operation.trxID = self.getNum(parts[1])
                operation.varID = self.getNum(parts[2])
                operation.writesToVal = self.getNum(parts[3])
                
            elif action == "R":
                operation.action = Action.READ
                operation.trxID = self.getNum(parts[1])
                operation.varID = self.getNum(parts[2])
                
            elif action == "fail":
                operation.action = Action.FAIL
                operation.siteID = self.getNum(parts[1])
                
            elif action == "recover":
                operation.action = Action.RECOVER
                operation.siteID = self.getNum(parts[1])
                
            elif action == "dump":
                operation.action = Action.DUMP
            self.operations.append(operation)
            self.currentTime += 1
        f.close()

    def getNum(self, s):
        for i in range(len(s)):
            if not s[i].isdigit():
                continue
            return int(s[i:])
        return -1
