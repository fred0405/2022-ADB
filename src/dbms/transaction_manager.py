from collections import deque

from .constants import Action, TransactionStatus
from .input_parser import Operation, Parser

class Transaction:
    def __init__(self, start_time: int, id: int) -> None:
        self.id = id
        self.start_time = start_time
        self.is_read_only = False
        self.status = TransactionStatus.ACTIVE
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
        trx = Transaction(operation.timestamp, operation.txn_id)
        self.idToTransactions[trx.id] = trx
        print('[INFO]', f'T{trx.id} begins')

    def initROTransaction(self, operation: Operation):
        currTime = operation.timestamp
        trx = Transaction(currTime, operation.txn_id)
        trx.is_read_only = True
        
        data = dict()
        for site in self.idToSites.values():
            if site.is_down:
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
        trx = self.idToTransactions.get(operation.txn_id)
        if trx.status == TransactionStatus.ABORTED or trx.status == TransactionStatus.ABORTING:
            print('[RW_FAIL]', f'T{trx.id} can\'t be executed because it is aborted or will be aborted')
            return
        if operation.action == Action.READ:
            self.read(operation)
        elif operation.action == Action.WRITE:
            self.write(operation)
        self.detect_and_resolve_deadlock()

    def read(self, operation: Operation):
        trxId = operation.txn_id
        trx = self.idToTransactions.get(trxId)
        if trx.is_read_only:
            self.readROValue(operation)
            return
        varId = operation.var_id
        if self.canRead(varId, trxId):
            self.readValue(operation)
            self._addReadLock(varId, trxId)
        else:
            self.putOperationOnHold(operation)

    def readROValue(self, operation: Operation):
        trxId = operation.txn_id
        varId = operation.var_id
        trx = self.idToTransactions.get(trxId)

        if len(trx.data) != 0 and varId in trx.data:
            print('[INFO]', f'T{trx.id} reads x{varId}: {trx.data[varId]}')
        else:
            print('[INFO]', f'T{trxId} can\'t read x{varId} because no valid version is available')
            self.abort(trxId)

    def readValue(self, operation: Operation):
        trxId = operation.txn_id
        varId = operation.var_id
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
            lockManager = site.lock_manager
            if not lockManager.canRead(varId, trxId):
                return False
            for op in self.waitingOperations:
                if op.var_id == varId and op.action == Action.WRITE:
                    return False
            if varId in site.nonReplicatedVarIds or (varId in site.replicatedVarIds and varId not in site.lock_manager.varsWaitingForCommittedWrites):
                canRead = True
        return canRead

    def _addReadLock(self, varId, trxId):
        for site in self.getAvailSitesHoldingVarId(varId):
            site.lock_manager.addReadLock(varId, trxId)

    def write(self, operation: Operation):
        trxId = operation.txn_id
        varId = operation.var_id
        writeToVal = operation.var_val
        if self.canWrite(varId, trxId):
            # print("[OK_TO_WRITE]", operation)
            self._addWriteLock(varId, trxId)
            self._writeValue(varId, writeToVal, trxId)
            self._print_write_intent(operation)
        else:
            print("[WRITE_ON_HOLD]", operation)
            self.putOperationOnHold(operation)

    def _writeValue(self, varId, writeToVal, trxId):
        for site in self.getAvailSitesHoldingVarId(varId):
            site.writeValue(varId, writeToVal, trxId)

    def _print_write_intent(self, operation: Operation):
        trxId = operation.txn_id
        varId = operation.var_id
        writeToVal = operation.var_val
        sb = f'T{trxId} writes x{varId}: {writeToVal} to site(s): '
        site_ids = [s.id for s in self.getAvailSitesHoldingVarId(varId)]
        sb += ' '.join([str(sid) for sid in sorted(site_ids)])
        print('[INFO]', sb)

    def canWrite(self, varId, trxId):
        sites = self.getAvailSitesHoldingVarId(varId)
        if not sites:
            return False
        for site in sites:
            if not site.lock_manager.canWrite(varId, trxId):
                return False
            for op in self.waitingOperations:
                if op.var_id == varId and op.action == Action.WRITE:
                    return False
        return True

    def _addWriteLock(self, varId, trxId):
        for site in self.getAvailSitesHoldingVarId(varId):
            site.lock_manager.addWriteLock(varId, trxId)

    def putOperationOnHold(self, operation: Operation):
        trxId = operation.txn_id
        varId = operation.var_id
        availSites = self.getAvailSitesHoldingVarId(varId)

        # (1) no site is available
        if not availSites:
            self.waitingOperations.append(operation)
            print('[NO_AVAIL_SITE]', f'T{trxId} waits because all sites holding the variable are down')
            return

        # (2) operation in the recovered site which waiting for committed write
        if operation.action == Action.READ:
            for site in availSites:
                if varId in site.lock_manager.varsWaitingForCommittedWrites:
                    print('[WAIT_FOR_COMMIT]', f'T{trxId} waits because x{varId} is waiting for committed write at site {site.id}')
                    break
        
        # (3) operation should execute after some of waiting operations
        shouldWait = False
        for site in availSites:
            lockManager = site.lock_manager
            if shouldWait or (not lockManager.canRead(varId, trxId) and not lockManager.canWrite(varId, trxId)):
                break
            for op in self.waitingOperations:
                if op.var_id == varId and op.action == Action.WRITE:
                    if op.txn_id not in self.waitsForGraph:
                        self.waitsForGraph[op.txn_id] = set()
                    self.waitsForGraph[op.txn_id].add(trxId)
                    print('[ON_HOLD_WAIT]', f'T{trxId} waits because it cannot skip T{op.txn_id}')
                    shouldWait = True
                    break
        # (4) operation is on hold because of lock conflict
        self.waitingOperations.append(operation)
        locked = False
        lockHolders = self._getLockHolders(operation)
        if lockHolders:
            for lockedId in lockHolders:
                if lockedId not in self.waitsForGraph:
                    self.waitsForGraph[lockedId] = set()
                self.waitsForGraph[lockedId].add(trxId)
                locked = True
        if locked:
            print('[LOCK_CONFLICT]', f'T{trxId} waits for T{lockHolders}')
        # self.print_wait_graph()

    def getAvailSitesHoldingVarId(self, varId):
        ret = set()
        for site in self.idToSites.values():
            if not site.is_down and (varId in site.replicatedVarIds or varId in site.nonReplicatedVarIds):
                ret.add(site)
        return list(ret)

    def _getLockHolders(self, operation: Operation):
        lockHolders = set()
        varId = operation.var_id
        txn_id = operation.txn_id
        sites = self.getAvailSitesHoldingVarId(varId)
        for site in sites:
            lockManager = site.lock_manager
            readLocks = lockManager.readLocks
            writeLocks = lockManager.writeLocks

            if varId in readLocks:
                lockHolders.update(readLocks[varId])
            if varId in writeLocks:
                lockHolders.add(writeLocks[varId])

        if txn_id in lockHolders:
            lockHolders.remove(txn_id)
        return lockHolders

    def detect_and_resolve_deadlock(self):
        for trxId in self.idToTransactions.keys():
            visited = set()
            if self._has_cycle(trxId, visited):
                self._abort_youngest_txn(visited)
                return
                
    def _has_cycle(self, currTrxId, visited):
        if currTrxId in visited:
            return True
        if currTrxId not in self.waitsForGraph:
            return False
        visited.add(currTrxId)
        for waitingTrxId in self.waitsForGraph[currTrxId]:
            if self._has_cycle(waitingTrxId, visited):
                return True
        visited.remove(currTrxId)
        return False

    def _abort_youngest_txn(self, visited):
        youngestTrxId = -1
        largestTime = -1
        for trxId in visited:
            trx = self.idToTransactions.get(trxId)
            if trx.start_time > largestTime:
                largestTime = trx.start_time
                youngestTrxId = trxId
        print('[DEADLOCK_DETECTED]', f'kill youngest transaction T{youngestTrxId}')
        self.abort(youngestTrxId)

    def end(self, operation: Operation):
        trxId = operation.txn_id
        currTime = operation.timestamp
        trx = self.idToTransactions.get(trxId)
        if trx.status == TransactionStatus.ABORTED:
            return
        if trx.status == TransactionStatus.ABORTING:
            self.abort(trxId)
            return
        self.commit(trxId, currTime)

    def commit(self, trxId, currTime):
        trx = self.idToTransactions.get(trxId)
        trx.status = TransactionStatus.COMMITTED
        self.commit_or_abort(trxId, True, currTime)
        print('[INFO]', f'T{trxId} commits')

    def abort(self, trxId):
        trx = self.idToTransactions.get(trxId)
        trx.status = TransactionStatus.ABORTED
        self.commit_or_abort(trxId, False, None)
        print('[INFO]', f'T{trxId} aborts')
    
    def commit_or_abort(self, trxId, shouldCommit, currTime):
        if shouldCommit and currTime == None:
            return
        
        # (1) Remove transaction in waitsForGraph
        self._remove_from_wait_graph(trxId)
        temp = []
        for op in self.waitingOperations:
            if op.txn_id == trxId:
                temp.append(op)
        
        # (2) Remove transaction in waiting operation
        for op in temp:
            self.waitingOperations.remove(op)
        del temp

        committedWrittenVarIds = set()
        if shouldCommit:
            self._commit_value(trxId, currTime, committedWrittenVarIds)
        else:
            self._revert_value(trxId)
        
        lockedVarIds = self._get_locked_vars(trxId)
        lockedVarIds.update(committedWrittenVarIds)
        # (3) release transaction's locks
        self._release_all_locks(trxId)
        # (4) wake up waiting operations
        self._wake_up_waiting_ops(lockedVarIds)

    def _wake_up_waiting_ops(self, lockedVarIds):
        opsToWakeUp = deque()
        for lockedVarId in lockedVarIds:
            for op in self.waitingOperations:
                if op.var_id == lockedVarId and op not in opsToWakeUp:
                    opsToWakeUp.append(op)
        if not opsToWakeUp:
            return
        for op in opsToWakeUp:
            print('[WAKE_UP_OP]', op)
            self.waitingOperations.remove(op)
            self.pending_operations.append(op)
        
    def _remove_from_wait_graph(self, trxId):
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

    def _get_locked_vars(self, trxId):
        lockVariable = set()
        for site in self.idToSites.values():
            lockVariable.update(site.lock_manager.getLockedVariables(trxId))
        return lockVariable

    def _release_all_locks(self, trxId):
        for site in self.idToSites.values():
            site.lock_manager.releaseAllLocks(trxId)

    def _commit_value(self, txn_id, currTime, committedWrittenVarIds):
        for site in self.idToSites.values():
            committedWrittenVarIds.update(site.writtenVarIds)
            site.commitValue(txn_id, currTime)

    def _revert_value(self, trxId):
        for site in self.idToSites.values():
            site.revertValue(trxId)

    def fail(self, operation: Operation):
        siteId = operation.site_id
        currTime = operation.timestamp

        site = self.idToSites.get(siteId)
        site.fail(currTime)
        affected_txns = []
        for trx in self.idToTransactions.values():
            if trx.id in site.visitedTrxIds:
                if trx.status == TransactionStatus.ABORTED:
                    # txn already aborted
                    site.visitedTrxIds.remove(trx.id)
                else:
                    trx.status = TransactionStatus.ABORTING
                    affected_txns.append(trx.id)
        print('[INFO]', f'Site {siteId} is down')
        if affected_txns:
            print('[AFFECTED_TXNS]', f'T{affected_txns} should abort')

    def recover(self, operation):
        siteId = operation.site_id
        site = self.idToSites.get(siteId)
        site.recover(operation.timestamp)
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
    
