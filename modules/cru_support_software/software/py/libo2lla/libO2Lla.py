"""Dummy class to run without the FLP"""

class Session():

    def __init__(self, sessionName, cardId):
        pass
    def start(self):
        return True
    def timedStart(self,timeOut):
        return True
    def stop(self):
        pass
