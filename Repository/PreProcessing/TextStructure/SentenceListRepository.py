from Repository import _BaseRepository as BaseRepository
from Entity.PreProcessing.TextStructure import _SentenceList as SentenceList

class SentenceListRepository(BaseRepository):

    def Get(self, id):
        return self.session.query(SentenceList).filter(SentenceList.id == id).first()
    
    def GetByPreProcessStepChainNode(self, preProcessStepChainNode):
        return self.session.query(SentenceList).\
            filter(SentenceList.preProcessStepChainNode == preProcessStepChainNode).all()

    def Hello(self):
        print ('Hello, I\'m a repository')

    def __init__(self):
        super().__init__()