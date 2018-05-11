from Repository import _BaseRepository as BaseRepository
from Entity.PreProcessing.TextStructure import _Sentence as Sentence

class SentenceRepository(BaseRepository):

    def Get(self, id):
        return self.session.query(Sentence).filter(Sentence.id == id).first()

    def Hello(self):
        print ('Hello, I\'m a repository')

    def __init__(self):
        super().__init__()
