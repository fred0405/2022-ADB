import sys
from IO import *
from Site import *
from TransactionManager import *
from DataType import *


def initSites(idToSites):
    for i in range(1, 11):
        idToSites[i] = Site(i)
    for varId in range(1, 21):
        for siteId in range(1, 11):
            site = idToSites.get(siteId)

            if varId % 2 == 0:
                site.initVarValues(varId, DataType.REPLICATED)
            else:
                targetSiteId = 1 + varId % 10
                if siteId == targetSiteId:
                    site.initVarValues(varId, DataType.NON_REPLICATED)


if __name__ == '__main__':
    io = IO('./test1.txt', './output1.txt')
    io.parseFile()
    idToSites = dict()
    initSites(idToSites)
    transactionManager = TransactionManager(io.operations, idToSites)
    transactionManager.simulate()
