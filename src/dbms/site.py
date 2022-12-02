from .lock_manager import LockManager
from .constants import DataType
from .utils import Interval

class Site:
    def __init__(self, id: int) -> None:
        self.lockManager = LockManager()
        self.id = id
        self.isDown = False

        self.replicatedVarIds = list()
        self.nonReplicatedVarIds = list()
        self.varToCommittedVal = dict()
        self.varToCommittedTime = dict()
        self.varToCurrVal = dict()
        self.terminatedIntervals = list()
        self.visitedTrxIds = set()
        self.writtenVarIds = set()

    def initVarValues(self, varId: int, datatype: DataType):
        if datatype == DataType.REPLICATED:
            self.replicatedVarIds.append(varId)
        else:
            self.nonReplicatedVarIds.append(varId)
        
        self.varToCommittedVal[varId] = varId * 10
        self.varToCommittedTime[varId] = 0
        self.varToCurrVal[varId] = varId * 10

    def readValue(self, varId: int, trxId: int):
        self.visitedTrxIds.add(trxId)
        return self.varToCurrVal.get(varId)

    def writeValue(self, varId: int, writeToVal: int, trxId: int):
        #print("///write site", self.id, varId, writeToVal, trxId)
        self.varToCurrVal[varId] = writeToVal
        self.visitedTrxIds.add(trxId)
        self.writtenVarIds.add(varId)

    def commitValue(self, txn_id: int, currTime: int):
        if self.isDown:
            return 
        lockVariables = self.lockManager.getLockedVariables(txn_id)
        for varId in lockVariables:
            self.varToCommittedVal[varId] = self.varToCurrVal.get(varId)
            self.varToCommittedTime[varId] = currTime

        # Remove trxId from visitedTrxIds (Used for fail site. When site fails, this
        # transaction is no longer affected).
        if txn_id in self.visitedTrxIds:
            self.visitedTrxIds.remove(txn_id)

        # Remove varIds which transaction modified from lockManager's
        # varsWaitingForCommittedWrites and clear writtenVarIds. (Used for recovery
        # site release read locks)
        for varId in self.writtenVarIds:
            if varId in self.lockManager.varsWaitingForCommittedWrites:
                self.lockManager.varsWaitingForCommittedWrites.remove(varId)
        self.writtenVarIds.clear()

    def fail(self, timestamp: int):
        self.isDown = True
        self.revertAllValues() # waiting to implement
        self.lockManager.clear()
        if len(self.terminatedIntervals) == 0 or self.terminatedIntervals[-1].isClosed:
            self.terminatedIntervals.append(Interval(timestamp))

    def recover(self, timestamp: int):
        self.isDown = False
        self.lockManager.varsWaitingForCommittedWrites.update(self.replicatedVarIds)
        if len(self.terminatedIntervals) != 0 and self.terminatedIntervals[-1].isClosed:
            self.terminatedIntervals[-1].endTime = timestamp - 1

    def isSiteFailInPeriod(self, startTime: int, endTime: int):
        for i in range(len(self.terminatedIntervals)):
            interval = self.terminatedIntervals[i]
            if interval.endTime < startTime:
                continue
            return interval.startTime <= endTime
        return False

    def revertValue(self, trxId: int):
        lockVariables = self.lockManager.getLockedVariables(trxId)
        for varId in lockVariables:
            self.varToCurrVal[varId] = self.varToCommittedVal.get(varId)

    def revertAllValues(self):
        self.varToCurrVal = self.varToCommittedVal
