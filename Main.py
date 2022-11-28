import sys
from IO import *
from Site import *
from TransactionManager import *
from DataType import *


class DB():
    NUM_OF_SITES = 10
    NUM_OF_VARS = 20

    def __init__(self):
        self.sites = {}

        self.init_sites()
    
    def init_sites(self):
        for i in range(1, 1 + self.NUM_OF_SITES):
            self.sites[i] = Site(i)

        for i in range(1, 1 + self.NUM_OF_VARS):
            for site_id, site in self.sites.items():
                if i % 2 == 0:
                    site.initVarValues(i, DataType.REPLICATED)
                elif site_id == 1 + i % 10:
                    site.initVarValues(i, DataType.NON_REPLICATED)

    def run(self, ops):
        transactionManager = TransactionManager(ops, self.sites)
        transactionManager.simulate()


if __name__ == '__main__':
    io = IO('./test/test1', './output1')
    io.parseFile()

    db = DB()
    db.run(io.operations)
