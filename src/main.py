from dbms.IO import IO
from dbms.site import Site
from dbms.TransactionManager import TransactionManager
from dbms.constants import DataType

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
                    # Even indexed variables are at all sites
                    site.initVarValues(i, DataType.REPLICATED)
                elif site_id == 1 + i % 10:
                    # Odd indexed variables are at one site each
                    # (i.e. 1 + (index_number mod 10) )
                    site.initVarValues(i, DataType.NON_REPLICATED)

    def run(self, ops):
        transactionManager = TransactionManager(ops, self.sites)

        transactionManager.start()

if __name__ == '__main__':
    io = IO()
    db = DB()
    db.run(io.operations)
