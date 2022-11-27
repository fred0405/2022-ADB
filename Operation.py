class Operation:
    def __init__(self) -> None:
        self.timeStamp = None
        self.action = None
        self.trxID = None
        self.varID = None
        self.siteID = None
        self.writesToVal = None

    def __str__(self) -> str:
        ret = ''
        ret += f'Timestamp: {self.timeStamp} \n'
        ret += f'Action: {self.action} \n'
        ret += f'Trx ID: {self.trxID} \n'
        ret += f'Var ID: {self.varID} \n'
        ret += f'Site ID: {self.siteID} \n'
        ret += f'Write value: {self.writesToVal} \n'
        return ret