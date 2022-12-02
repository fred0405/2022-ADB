from collections import deque

from .constants import Action, TransactionStatus
from .input_parser import Operation, Parser

class Transaction:
    def __init__(self, beginTime: int, id: int) -> None:
        self.beginTime = beginTime
        self.id = id
        self.status = TransactionStatus.ACTIVE
        self.isReadyOnly = False
        self.data = dict()


class TransactionManager:
    def __init__(self, idToSites: dict) -> None:
        self.pending_operations = deque()
        self.idToTransactions = dict()
        self.idToSites = idToSites
        self.waitingOperations = list()
        self.waitsForGraph = dict()

        self.action_handlers = {
            Action.BEGIN: self.initTransaction,
            Action.BEGIN_RO: self.initROTransaction,
            Action.READ: self.readOrWrite,
            Action.WRITE: self.readOrWrite,
            Action.END: self.end,
            Action.FAIL: self.fail,
            Action.RECOVER: self.recover,
            Action.DUMP: self.dump,
        }

    def start(self) -> None:
        parser = Parser()
        while True:
            if self.pending_operations:
                ops_todo = self.pending_operations
                self.pending_operations = []
                for pending_op in ops_todo:
                    self._handle_operation(pending_op)
            try:
                op = parser.parse_line()
            except EOFError:
                break
            if not op:
                continue
            if op.action in self.action_handlers:
                self._handle_operation(op)

    def _handle_operation(self, op: Operation) -> None:
        self.action_handlers[op.action](op)

    def initTransaction(self, operation: Operation):
        trx = Transaction(operation.timeStamp, operation.trxID)
        self.idToTransactions[trx.id] = trx
        print('[INFO]', f'T{trx.id} begins')

    def initROTransaction(self, operation: Operation):
        currTime = operation.timeStamp
        trx = Transaction(currTime, operation.trxID)
        trx.isReadyOnly = True
        
        data = dict()
        for site in self.idToSites.values():
            if site.isDown:
                continue
            for varId in site.nonReplicatedVarIds:
                data[varId] = site.varToCommittedVal.get(varId)
            
            for varId in site.replicatedVarIds:
                committedTime = site.varToCommittedTime.get(varId)
                if not site.isSiteFailInPeriod(committedTime, currTime) and varId not in data:
                    data[varId] = site.varToCommittedVal.get(varId)
        trx.data = data
        self.idToTransactions[trx.id] = trx
        print('[INFO]', f'T{trx.id} begins as a read-only transaction')
 
    def readOrWrite(self, operation: Operation):
        trx = self.idToTransactions.get(operation.trxID)
        if trx.status == TransactionStatus.ABORTED or trx.status == TransactionStatus.SHOULD_ABORTED:
            print('[RW_FAIL]', f'T{trx.id} can\'t be executed because it is aborted or will be aborted')
            return
        if operation.action == Action.READ:
            self.read(operation)
        elif operation.action == Action.WRITE:
            self.write(operation)
        self.detectDeadLock()

    def read(self, operation: Operation):
        trxId = operation.trxID
        trx = self.idToTransactions.get(trxId)
        if trx.isReadyOnly:
            self.readROValue(operation)
            return
        varId = operation.varID
        if self.canRead(varId, trxId):
            self.readValue(operation)
            self.addReadLock(varId, trxId)
        else:
            self.putOperationOnHold(operation)

    def readROValue(self, operation: Operation):
        trxId = operation.trxID
        varId = operation.varID
        trx = self.idToTransactions.get(trxId)

        if len(trx.data) != 0 and varId in trx.data:
            print('[INFO]', f'T{trx.id} reads x{varId}: {trx.data[varId]}')
        else:
            print('[INFO]', f'T{trxId} can\'t read x{varId} because no valid version is available')
            self.abort(trxId)

    def readValue(self, operation: Operation):
        trxId = operation.trxID
        varId = operation.varID
        sites = self.getAvailSitesHoldingVarId(varId)
        if not sites:
            print('[READ_FAIL]', f'T{trxId} can\'t read x{varId} because all sites holding the variable are down')
            self.abort(trxId)
        else:
            site = sites[0]
            readVal = site.readValue(varId, trxId)
            print('[INFO]', f'T{trxId} reads x{varId}: {readVal}')

    def canRead(self, varId, trxId):
        sites = self.getAvailSitesHoldingVarId(varId)
        if not sites:
            return False
        canRead = False
        for site in sites:
            lockManager = site.lockManager
            if not lockManager.canRead(varId, trxId):
                return False
            for op in self.waitingOperations:
                if op.varID == varId and op.action == Action.WRITE:
                    return False
            if varId in site.nonReplicatedVarIds or (varId in site.replicatedVarIds and varId not in site.lockManager.varsWaitingForCommittedWrites):
                canRead = True
        return canRead

    def addReadLock(self, varId, trxId):
        for site in self.getAvailSitesHoldingVarId(varId):
            site.lockManager.addReadLock(varId, trxId)

    def write(self, operation: Operation):
        trxId = operation.trxID
        varId = operation.varID
        writeToVal = operation.writesToVal
        if self.canWrite(varId, trxId):
            # print("[OK_TO_WRITE]", operation)
            self.addWriteLock(varId, trxId)
            self.writeValue(varId, writeToVal, trxId)
            self.printSitesAffectedByTheWrite(operation)
        else:
            print("[WRITE_ON_HOLD]", operation)
            self.putOperationOnHold(operation)

    def writeValue(self, varId, writeToVal, trxId):
        for site in self.getAvailSitesHoldingVarId(varId):
            site.writeValue(varId, writeToVal, trxId)

    def printSitesAffectedByTheWrite(self, operation: Operation):
        trxId = operation.trxID
        varId = operation.varID
        writeToVal = operation.writesToVal
        sb = f'T{trxId} writes x{varId}: {writeToVal} to site(s): '
        site_ids = [s.id for s in self.getAvailSitesHoldingVarId(varId)]
        sb += ' '.join([str(sid) for sid in sorted(site_ids)])
        print('[INFO]', sb)

    def canWrite(self, varId, trxId):
        sites = self.getAvailSitesHoldingVarId(varId)
        if not sites:
            return False
        for site in sites:
            if not site.lockManager.canWrite(varId, trxId):
                return False
            for op in self.waitingOperations:
                if op.varID == varId and op.action == Action.WRITE:
                    return False
        return True

    def addWriteLock(self, varId, trxId):
        for site in self.getAvailSitesHoldingVarId(varId):
            site.lockManager.addWriteLock(varId, trxId)

    def putOperationOnHold(self, operation: Operation):
        trxId = operation.trxID
        varId = operation.varID
        availSites = self.getAvailSitesHoldingVarId(varId)

        # (1) no site is available
        if not availSites:
            self.waitingOperations.append(operation)
            print('[NO_AVAIL_SITE]', f'T{trxId} waits because all sites holding the variable are down')
            return

        # (2) operation in recovered site which waiting for committed write
        if operation.action == Action.READ:
            for site in availSites:
                if varId in site.lockManager.varsWaitingForCommittedWrites:
                    print('[WAIT_FOR_COMMIT]', f'T{trxId} waits because x{varId} is waiting for committed write at site {site.id}')
                    break
        
        # (3) operation should execute after some of waiting operations
        shouldWait = False
        for site in availSites:
            lockManager = site.lockManager
            if shouldWait or (not lockManager.canRead(varId, trxId) and not lockManager.canWrite(varId, trxId)):
                break
            for op in self.waitingOperations:
                if op.varID == varId and op.action == Action.WRITE:
                    if op.trxID not in self.waitsForGraph:
                        self.waitsForGraph[op.trxID] = set()
                    self.waitsForGraph[op.trxID].add(trxId)
                    print('[ON_HOLD_WAIT]', f'T{trxId} waits because it cannot skip T{op.trxID}')
                    shouldWait = True
                    break
        # (4) operation is on hold because of lock conflict
        self.waitingOperations.append(operation)
        locked = False
        lockHolders = self.getLockHolders(operation)
        if lockHolders:
            for lockedId in lockHolders:
                if lockedId not in self.waitsForGraph:
                    self.waitsForGraph[lockedId] = set()
                self.waitsForGraph[lockedId].add(trxId)
                locked = True
        if locked:
            print('[LOCK_CONFLICT]', f'T{trxId} waits for T{lockHolders}')
        # self.printWaitsForGraph()

    def getAvailSitesHoldingVarId(self, varId):
        ret = set()
        for site in self.idToSites.values():
            if not site.isDown and (varId in site.replicatedVarIds or varId in site.nonReplicatedVarIds):
                ret.add(site)
        return list(ret)

    def getLockHolders(self, operation: Operation):
        lockHolders = set()
        varId = operation.varID
        txn_id = operation.trxID
        sites = self.getAvailSitesHoldingVarId(varId)
        for site in sites:
            lockManager = site.lockManager
            readLocks = lockManager.readLocks
            writeLocks = lockManager.writeLocks

            if varId in readLocks:
                lockHolders.update(readLocks[varId])
            if varId in writeLocks:
                lockHolders.add(writeLocks[varId])

        if txn_id in lockHolders:
            lockHolders.remove(txn_id)
        return lockHolders

    def detectDeadLock(self):
        for trxId in self.idToTransactions.keys():
            visited = set()
            if self.hasCycle(trxId, visited):
                self.abortYoungestTrx(visited)
                return
                
    def hasCycle(self, currTrxId, visited):
        if currTrxId in visited:
            return True
        if currTrxId not in self.waitsForGraph:
            return False
        visited.add(currTrxId)
        for waitingTrxId in self.waitsForGraph[currTrxId]:
            if self.hasCycle(waitingTrxId, visited):
                return True
        visited.remove(currTrxId)
        return False

    def abortYoungestTrx(self, visited):
        youngestTrxId = -1
        largestTime = -1
        for trxId in visited:
            trx = self.idToTransactions.get(trxId)
            if trx.beginTime > largestTime:
                largestTime = trx.beginTime
                youngestTrxId = trxId
        print('[DEADLOCK_DETECTED]', f'kill youngest transaction T{youngestTrxId}')
        self.abort(youngestTrxId)

    def end(self, operation: Operation):
        trxId = operation.trxID
        currTime = operation.timeStamp
        trx = self.idToTransactions.get(trxId)
        if trx.status == TransactionStatus.ABORTED:
            return
        if trx.status == TransactionStatus.SHOULD_ABORTED:
            self.abort(trxId)
            return
        self.commit(trxId, currTime)

    def commit(self, trxId, currTime):
        trx = self.idToTransactions.get(trxId)
        trx.status = TransactionStatus.COMMITTED
        self.commitOrAbort(trxId, True, currTime)
        print('[INFO]', f'T{trxId} commits')

    def abort(self, trxId):
        trx = self.idToTransactions.get(trxId)
        trx.status = TransactionStatus.ABORTED
        self.commitOrAbort(trxId, False, None)
        print('[INFO]', f'T{trxId} aborts')
    
    def commitOrAbort(self, trxId, shouldCommit, currTime):
        if shouldCommit and currTime == None:
            return
        
        # (1) Remove transaction in waitsForGraph
        self.removeFromWaitsForGraph(trxId)
        temp = []
        for op in self.waitingOperations:
            if op.trxID == trxId:
                temp.append(op)
        
        # (2) Remove transaction in waiting operation
        for op in temp:
            self.waitingOperations.remove(op)
        del temp

        committedWrittenVarIds = set()
        if shouldCommit:
            self.commitValue(trxId, currTime, committedWrittenVarIds)
        else:
            self.revertValue(trxId)
        
        lockedVarIds = self.getLockVariables(trxId)
        lockedVarIds.update(committedWrittenVarIds)
        # (3) release transaction's locks
        self.releaseAllLocks(trxId)
        # (4) wake up waiting operations
        self.wakeUpWaitingOperations(lockedVarIds)

    def wakeUpWaitingOperations(self, lockedVarIds):
        opsToWakeUp = deque()
        for lockedVarId in lockedVarIds:
            for op in self.waitingOperations:
                if op.varID == lockedVarId and op not in opsToWakeUp:
                    opsToWakeUp.append(op)
        if not opsToWakeUp:
            return
        for op in opsToWakeUp:
            print('[WAKE_UP_OP]', op)
            self.waitingOperations.remove(op)
            self.pending_operations.append(op)
        
    def removeFromWaitsForGraph(self, trxId):
        emptyTrx = list()
        for key, value in self.waitsForGraph.items():
            if trxId in value:
                value.remove(trxId)
            if len(value) == 0:
                emptyTrx.append(key)
        for key in emptyTrx:
            self.waitsForGraph.pop(key, None)
        self.waitsForGraph.pop(trxId, None)
        # self.printWaitsForGraph()

    def getLockVariables(self, trxId):
        lockVariable = set()
        for site in self.idToSites.values():
            lockVariable.update(site.lockManager.getLockedVariables(trxId))
        return lockVariable

    def releaseAllLocks(self, trxId):
        for site in self.idToSites.values():
            site.lockManager.releaseAllLocks(trxId)

    def commitValue(self, txn_id, currTime, committedWrittenVarIds):
        for site in self.idToSites.values():
            committedWrittenVarIds.update(site.writtenVarIds)
            site.commitValue(txn_id, currTime)

    def revertValue(self, trxId):
        for site in self.idToSites.values():
            site.revertValue(trxId)

    def fail(self, operation: Operation):
        siteId = operation.siteID
        currTime = operation.timeStamp

        site = self.idToSites.get(siteId)
        site.fail(currTime)
        affected_txns = []
        for trx in self.idToTransactions.values():
            if trx.id in site.visitedTrxIds:
                if trx.status == TransactionStatus.ABORTED:
                    # txn already aborted
                    site.visitedTrxIds.remove(trx.id)
                else:
                    trx.status = TransactionStatus.SHOULD_ABORTED
                    affected_txns.append(trx.id)
        print('[INFO]', f'Site {siteId} is down')
        if affected_txns:
            print('[AFFECTED_TXNS]', f'T{affected_txns} should abort')

    def recover(self, operation):
        siteId = operation.siteID
        currTime = operation.timeStamp
        site = self.idToSites.get(siteId)
        site.recover(currTime)
        print('[INFO]', f'Site {siteId} recovers')

    def dump(self, operation):
        for site in self.idToSites.values():
            varToCommittedVal = site.varToCommittedVal
            sb = ""
            delim = ''
            for varId in range(1, 21):
                if varId not in varToCommittedVal:
                    continue
                sb += delim + 'x' + str(varId) + ': ' + str(varToCommittedVal.get(varId))
                delim = ', '
            print(f'site {site.id} - {sb}')
    
    # def printWaitsForGraph(self):
    #     sb = ''
    #     sb += 'Size of waitsForGraph: ' + str(len(self.waitsForGraph)) + '\n'
    #     sb += '-----------------------------------------\n'
    #     for trxId in self.waitsForGraph.keys():
    #         sb += str(trxId) + ': '
    #         for waitingTrx in self.waitsForGraph.get(trxId):
    #             sb += str(waitingTrx) + ' '
    #         sb += '\n'
    #     sb += '-----------------------------------------\n'


    
    
    
    
            