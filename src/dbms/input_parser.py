from collections import deque
import re

from .constants import Action

class Operation:
    def __init__(self) -> None:
        self.timestamp = None
        self.action = None
        self.txn_id = None
        self.var_id = None
        self.site_id = None
        self.var_val = None

    def __repr__(self) -> str:
        ret = '('
        ret += f'Time:{self.timestamp} {self.action}'
        if self.txn_id is not None:
            ret += f' Txn:{self.txn_id}'
        if self.var_id is not None:
            ret += f' Var:{self.var_id}'
        if self.site_id is not None:
            ret += f' Site:{self.site_id}'
        if self.var_val is not None:
            ret += f' Write_var_val:{self.var_val}'
        return ret + ')'

class Parser:
    def __init__(self) -> None:
        self.current_time = 0
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
        op.timestamp = self.current_time
        if action == 'begin':
            op.action = Action.BEGIN
            op.txn_id = self._read_num(tokens[1])
        elif action == "beginRO":
            op.action = Action.BEGIN_RO
            op.txn_id = self._read_num(tokens[1])
        elif action == "end":
            op.action = Action.END
            op.txn_id = self._read_num(tokens[1])
        elif action == "W":
            op.action = Action.WRITE
            op.txn_id = self._read_num(tokens[1])
            op.var_id = self._read_num(tokens[2])
            op.var_val = self._read_num(tokens[3])
        elif action == "R":
            op.action = Action.READ
            op.txn_id = self._read_num(tokens[1])
            op.var_id = self._read_num(tokens[2])
        elif action == "fail":
            op.action = Action.FAIL
            op.site_id = self._read_num(tokens[1])
        elif action == "recover":
            op.action = Action.RECOVER
            op.site_id = self._read_num(tokens[1])
        elif action == "dump":
            op.action = Action.DUMP
        self.current_time += 1
        return op

    def _read_num(self, s):
        for i in range(len(s)):
            if not s[i].isdigit():
                continue
            return int(s[i:])
        return -1
