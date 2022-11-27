class LockManager:
    def __init__(self) -> None:
        self.readLocks = dict()
        self.writeLocks = dict()
        self.varsWaitingForCommittedWrites = set()

    def addWriteLock(self, varId, trxId):
        self.writeLocks[varId] = trxId

    def addReadLock(self, varId, trxId):
        if varId not in self.readLocks:
            self.readLocks[varId] = set()
        self.readLocks[varId].add(trxId)

    def canWrite(self, varId, trxId):
        if varId in self.writeLocks and self.writeLocks[varId] != trxId:
            return False
        if varId in self.writeLocks:
            blockTrxIds = self.readLocks.get(varId, set())
            return len(blockTrxIds) == 1 and trxId in blockTrxIds
        return True

    def canRead(self, varId, trxId):
        if varId in self.writeLocks and self.writeLocks[varId] == trxId:
            return True
        return varId not in self.writeLocks

    def releaseAllLocks(self, trxId):
        temp = []
        for key, s in self.readLocks.items():
            if trxId in s:
                s.remove(trxId)
            if len(s) == 0:
                temp.append(key)
        for key in temp:
            del self.readLocks[key]
        temp.clear()
        for key, val in self.writeLocks.items():
            if trxId == val:
                temp.append(key)
        for key in temp:
            del self.writeLocks[key]

    def getLockedVariables(self, trxId):
        lockVars = set()
        for varId in self.writeLocks.keys():
            if self.writeLocks[varId] == trxId:
                lockVars.add(varId)

        for varId in self.readLocks.keys():
            if trxId in self.readLocks[varId]:
                lockVars.add(varId)

        return lockVars
    
    def eraseAllTables(self):
        self.readLocks.clear()
        self.writeLocks.clear()

    def clear(self):
        self.eraseAllTables()
        self.varsWaitingForCommittedWrites.clear()

    def getAllReadLockTrxs(self):
        readLockTrxs = set()
        for trxs in self.readLocks.values():
            readLockTrxs.update(trxs)
        return readLockTrxs

    def getAllWriteLockTrxs(self):
        writeLockTrxs = set()
        for trx in self.writeLocks.values():
            writeLockTrxs.add(trx)
        return writeLockTrxs

    def getAllTrxHoldingLocks(self):
        trxs = set()
        trxs.update(self.getAllReadLockTrxs())
        trxs.update(self.getAllWriteLockTrxs())
        return trxs