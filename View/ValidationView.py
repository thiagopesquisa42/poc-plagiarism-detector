import Manager.TestManager

class ValidationView(object):

    def Hello(self):
        print ('Hello, I\'m the ValidationView')
        print ('And I shows the output of these managers:')
        self._testManager.Hello()

    _testManager = Manager.TestManager.TestManager()

    def __init__(self):
        pass