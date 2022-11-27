class Interval:
    def __init__(self, startTime: int) -> None:
        self.startTime = startTime
        self.isClosed = False
        self.endTime = -1