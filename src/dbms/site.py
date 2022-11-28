from .LockManager import LockManager
from .constants import DataType
from .Interval import Interval

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
        self.varToCurrVal[varId] = writeToVal
        self.visitedTrxIds.add(trxId)
        self.writtenVarIds.add(varId);

    def commitValue(self, trxId: int, currTime: int):
        if self.isDown:
            return 
        lockVariables = self.lockManager.getLockedVariables(trxId);
        for varId in lockVariables:
            self.varToCommittedVal[varId] = self.varToCurrVal.get(varId)
            self.varToCommittedTime[varId] = currTime
        self.visitedTrxIds.remove(trxId)

        for varId in self.writtenVarIds:
            self.lockManager.varsWaitingForCommittedWrites.remove(varId)
        self.writtenVarIds.clear()

    def fail(self, timeStamp: int):
        self.isDown = True
        self.revertAllValues() # waiting to implement
        self.lockManager.clear()
        if len(self.terminatedIntervals) == 0 or self.terminatedIntervals[-1].isClosed:
            self.terminatedIntervals.append(Interval(timeStamp))

    def recover(self, timeStamp: int):
        self.isDown = False
        self.lockManager.varsWaitingForCommittedWrites.update(self.replicatedVarIds)
        if len(self.terminatedIntervals) != 0 and self.terminatedIntervals[-1].isCloeds:
            self.terminatedIntervals[-1].endTime = timeStamp - 1

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
