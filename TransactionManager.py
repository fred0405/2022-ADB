from collections import deque
from Action import Action
from Operation import Operation
from Transaction import TransactionStatus, Transaction
from Site import Site
from IO import IO
class TransactionManager:
    def __init__(self, operations: deque, idToSites: dict) -> None:
        self.operations = operations
        self.idToTransactions = dict()
        self.idToSites = idToSites
        self.waitingOperations = list()
        self.waitsForGraph = dict()

    def simulate(self):
        while self.operations:
            currOperation = self.operations.popleft()
            currAction = currOperation.action
            
            if currAction == Action.BEGIN:
                self.initTransaction(currOperation)
                continue
            elif currAction == Action.BEGIN_RO:
                self.initROTransaction(currOperation)
                continue
            elif currAction == Action.READ:
                self.readOrWrite(currOperation)
                continue
            elif currAction == Action.WRITE:
                self.readOrWrite(currOperation)
                continue
            elif currAction == Action.END:
                self.end(currOperation)
                continue
            elif currAction == Action.FAIL:
                self.fail(currOperation)
                continue
            elif currAction == Action.RECOVER:
                self.recover(currOperation)
                continue
            elif currAction == Action.DUMP:
                self.dump();
                continue

    def initTransaction(self, operation: Operation):
        trx = Transaction(operation.timeStamp, operation.trxID)
        self.idToTransactions[trx.id] = trx
        print(f'T{trx.id} begins')

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
                    data[varId] = site.varToCommittedVal
        trx.data = data
        self.idToTransactions[trx.id] = trx
        print(f'T{trx.id} begins as a read-only transaction')
 
    def readOrWrite(self, operation: Operation):
        trx = self.idToTransactions.get(operation.trxID)
        if trx.status == TransactionStatus.ABORTED or trx.status == TransactionStatus.SHOULD_ABORTED:
            print(f'T{trx.id} can\'t be executed because it is aborted or will be aborted')
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
            print(f'T{trx.id} reads x{varId}: {trx.data.get(varId)}')
        else:
            print(f'T{trxId} can\'t read x{varId} because no valid version is available')
            self.abort(trxId);

    def readValue(self, operation: Operation):
        trxId = operation.trxID
        varId = operation.varID
        sites = self.getAvailSitesHoldingVarId(varId)
        if not sites:
            print(f'T{trxId} can\'t read x{varId} because all sites holding the variable are down')
            self.abort(trxId)
        else:
            site = sites[0]
            readVal = site.readValue(varId, trxId)
            print(f'T{trxId} reads x{varId}: {readVal}')

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
            self.addWriteLock(varId, trxId)
            self.writeValue(varId, writeToVal, trxId)
            self.printSitesAffectedByTheWrite(operation)
        else:
            self.putOperationOnHold(operation)

    def writeValue(self, varId, writeToVal, trxId):
        for site in self.getAvailSitesHoldingVarId(varId):
            site.writeValue(varId, writeToVal, trxId)

    def printSitesAffectedByTheWrite(self, operation: Operation):
        trxId = operation.trxID
        varId = operation.varID
        writeToVal = operation.writesToVal
        sb = f'T{trxId} writes x{varId} with value {writeToVal}. Sites affected by the write are: '
        for site in self.getAvailSitesHoldingVarId(varId):
            sb += str(site.id) + ' '
        print(sb)

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
        if not availSites:
            self.waitingOperations.append(operation)
            print(f'T{trxId} waits because all sites holding the variable are down')
            return

        if operation.action == Action.READ:
            for site in availSites:
                if varId in site.lockManager.varsWaitingForCommittedWrites:
                    print(f'T{trxId} waits because x{varId} is waiting committed write takes place on the site')
                    break
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
                    print(f'T{trxId} waits because it cannot skip T {op.trxID}')
                    shouldWait = True
                    break
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
                print(f'T{trxId} waits because of lock conflict')
            self.printWaitsForGraph()

    def getAvailSitesHoldingVarId(self, varId):
        ret = set()
        for site in self.idToSites.values():
            if not site.isDown and (varId in site.replicatedVarIds or varId in site.nonReplicatedVarIds):
                ret.add(site)
        return list(ret)

    def getLockHolders(self, operation: Operation):
        lockHolders = set()
        varId = operation.varID
        sites = self.getAvailSitesHoldingVarId(varId)
        for site in sites:
            lockManager = site.lockManager
            readLocks = lockManager.readLocks
            writeLocks = lockManager.writeLocks

            if varId in readLocks:
                lockHolders.update(readLocks[varId])
            
            if varId in writeLocks:
                lockHolders.update(writeLocks[varId])
        lockHolders.remove(operation.trxID)
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
        print("DeadLoock detected")
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
        print(f'T{trxId} commits')

    def abort(self, trxId):
        trx = self.idToTransactions.get(trxId)
        trx.status = TransactionStatus.ABORTED
        self.commitOrAbort(trxId, False, None)
        print(f'T{trxId} aborts')
    
    def commitOrAbort(self, trxId, shouldCommit, currTime):
        if shouldCommit and currTime == None:
            return
        self.removeFromWaitsForGraph(trxId)
        temp = []
        for op in self.waitingOperations:
            if op.trxID == trxId:
                temp.append(op)
        for op in temp:
            self.waitingOperations.remove(op)
        del temp

        committedWrittenVarIds = set()
        if shouldCommit:
            self.commitValue(trxId, currTime, committedWrittenVarIds)
        else:
            self.revertValue(trxId)
        
        lockedVarIds = self.getLockVariables(trxId)
        self.releaseAllLocks(trxId)
        self.wakeUpWaitingOperations(lockedVarIds)

    def wakeUpWaitingOperations(self, lockedVarIds):
        opsToWakeUp = deque()
        for lockedVarId in lockedVarIds:
            for op in self.waitingOperations:
                if op.varID == lockedVarId and op not in opsToWakeUp:
                    opsToWakeUp.appendleft(op)

        for op in opsToWakeUp:
            self.waitingOperations.remove(op)
            self.operations.append(op)
        
    def removeFromWaitsForGraph(self, trxId):
        emptyTrx = list()
        for key, value in self.waitsForGraph.items():
            value.remove(trxId)
            if len(value) == 0:
                emptyTrx.append(key)
        for key in emptyTrx:
            self.waitsForGraph.pop(key, None)
        self.waitsForGraph.pop(trxId, None)
        self.printWaitsForGraph()

    def getLockVariables(self, trxId):
        lockVariable = set()
        for site in self.idToSites.values():
            lockVariable.update(site.lockManager.getLockedVariables(trxId))
        return lockVariable

    def releaseAllLocks(self, trxId):
        for site in self.idToSites.values():
            site.lockManager.releaseAllLocks(trxId)

    def commitValue(self, trxId, currTime, committedWrittenVarIds):
        for site in self.idToSites.values():
            committedWrittenVarIds.update(site.writtenVarIds)
            site.commitValue(trxId, currTime)

    def revertValue(self, trxId):
        for site in self.idToSites.values():
            site.revertValue(trxId)

    def fail(self, operation: Operation):
        siteId = operation.siteID
        currTime = operation.timeStamp

        site = self.idToSites.get(siteId)
        site.fail(currTime)
        for trx in self.idToTransactions.values():
            if trx.id in site.visitedTrxIds:
                trx.status = TransactionStatus.SHOULD_ABORTED
        print(f'Site {siteId} is down')

    def recover(self, operation):
        siteId = operation.siteID
        currTime = operation.timeStamp
        site = self.idToSites.get(siteId)
        site.recover(currTime)
        print(f'Site {siteId} recovers')

    def dump(self):
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
    
    
    
    def printWaitsForGraph(self):
        sb = ''
        sb += 'Size of waitsForGraph: ' + str(len(self.waitsForGraph)) + '\n'
        sb += '-----------------------------------------\n'
        for trxId in self.waitsForGraph.keys():
            sb += str(trxId) + ': '
            for waitingTrx in self.waitsForGraph.get(trxId):
                sb += str(waitingTrx) + ' '
            sb += '\n'
        sb += '-----------------------------------------\n'


    
    
    
    
            