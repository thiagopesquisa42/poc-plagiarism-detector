from itertools import groupby
import math

from Process import _BaseProcess as BaseProcess
from Entity.Seeding import _SeedingData as SeedingData
from Entity.Seeding import _Seed as Seed
from Entity.Seeding import _SeedAttributes as SeedAttributes
from Entity import _PlagiarismClass as PlagiarismClass
from Repository import _BaseRepository as BaseRepository
from Repository.PreProcessing import _PreProcessedDataRepository as PreProcessedDataRepository
from Repository.PreProcessing.TextStructure import _SentenceListRepository as SentenceListRepository
from Repository import _RawTextPairRepository as RawTextPairRepository
from Repository.Seeding import _SeedRepository as SeedRepository
from Repository.Seeding import _SeedingDataRepository as SeedingDataRepository
from Repository import _DetectionRepository as DetectionRepository
from constant import Threshold

class SeedingProcess(BaseProcess):

    def Hello(self):
        self.logger.info('Testing from SeedingProcess')
        print ('Hello, I\'m the SeedingProcess')

    def SeedingProcessing(self, preProcessedDataId):
        try:
            self.logger.info('Seeding Processing started')

            # self.logger.info('create Seeding Data Instance')
            # preProcessedData = self._preProcessedDataRepository.Get(id = preProcessedDataId)
            # seedingData = self.CreateSeedingData(preProcessedData)

            # self.logger.info('create seeds candidates')
            # rawTextPairList = self._rawTextPairRepository.GetListByTextCollectionMeta(seedingData.preProcessedData.textCollectionMeta)
            # seedCandidateList = self.CreateSeedCandidateListFromRawTextPairList(seedingData, rawTextPairList)

            
            # # [0] Create seeds candidates from 
            # #   all possible sentences suspicious-source-pairs in preprocessedData
            # self.logger.info('create seeds attributes registers')
            # self.CreateAttributesDefaultRegisterForSeeds(
            #     seedList = seedCandidateList)
            
            # # [1] Fill class (no-plag, obfuscated-plag...)
            # self.logger.info('label seeds detected')
            # self.LabelSeedList(seedingData, rawTextPairList)

            seedingData = self._seedingDataRepository.Get(id = 1)
            rawTextPairList = self._rawTextPairRepository.GetListByTextCollectionMeta(seedingData.preProcessedData.textCollectionMeta)
            # seedCandidateList = self._seedRepository.GetListBySeedingData(seedingData)
            # [2] Calculate attributes over bag-of-words and locations from both sentences
            self.logger.info('calculate seeds attributes')
            self.CalculateAttributesSeeedList(seedingData, rawTextPairList)

            print('')

        except Exception as exception:
            self.logger.info('Seeding Processing failure: ' + str(exception))
            raise exception
        else:
            self.logger.info('Seeding Processing finished')
    
    #region [Create seeding data]
    def CreateSeedingData(self, preProcessedData):
        seedingData = SeedingData(
            preProcessedData = preProcessedData,
            description = 'em testes')
        self._baseRepository.Insert(seedingData)
        return seedingData
    #end_region [Create seeding data]

    #region [Create seeds candidates]
    def CreateSeedCandidateListFromRawTextPairList(self, seedingData, rawTextPairList):
        for rawTextPair in rawTextPairList:
            self.CreateSeedCandidateList(seedingData, rawTextPair)
    
    def CreateSeedCandidateList(self, seedingData, rawTextPair):
        suspiciousSentenceList = self._sentenceListRepository.GetByRawText(
            rawText = rawTextPair.suspiciousRawText, 
            preProcessedData = seedingData.preProcessedData)
        sourceSentenceList = self._sentenceListRepository.GetByRawText(
            rawText = rawTextPair.sourceRawText, 
            preProcessedData = seedingData.preProcessedData)
        seedCandidateList = [
            Seed(seedingData = seedingData,
                suspiciousSentence = suspiciousSentence,
                sourceSentence = sourceSentence,
                rawTextPair = rawTextPair)
            for suspiciousSentence in suspiciousSentenceList.sentences
            for sourceSentence in sourceSentenceList.sentences]
        self._baseRepository.InsertList(seedCandidateList)
        return seedCandidateList

    def CreateAttributesDefaultRegisterForSeeds(self, seedList):
        seedAttributesList = [
            SeedAttributes(seed = seed)
            for seed in seedList]
        self._baseRepository.InsertList(seedAttributesList)
    #end_region [Create seeds candidates]

    #region [Fill seeds plagiarism class]
    def LabelSeedList(self, seedingData, rawTextPairList):
        commitList = []
        for rawTextPair in rawTextPairList:
            seedList = self._seedRepository.GetListByRawTextPair(rawTextPair, seedingData)
            seedList = self.LabelAllSeedAsNone(seedList)
            seedDetectedSet = self.LabelSeedAsDetection(seedList, rawTextPair)
            seedList = set(seedList)
            seedList.update(seedDetectedSet)
            commitList.extend(seedList)
        self._baseRepository.InsertList(commitList)

    def LabelAllSeedAsNone(self, seedList):
        for seed in seedList:
            seed.attributes.plagiarismClass = PlagiarismClass.none
        return seedList

    def LabelSeedAsDetection(self, seedList, rawTextPair):
        detectionList = self._detectionRepository.GetByRawTextPair(rawTextPair)
        if(detectionList is None or len(detectionList) == 0):
            return set()
        seedDetectedSet = self.GetSeedsInsideAnyDetection(detectionList, seedList)
        return seedDetectedSet

    def GetSeedsInsideAnyDetection(self, detectionList, seedList):
        seedSortedList = self.SortSeedListBySuspiciousSourceLocation(seedList)
        
        # get matrix seed indexed by suspicious and source locations
        seedMatrixLineSuspiciousColumnSource = [
            (
                location[0], 
                location[1],
                [(
                    seed.sourceSentence.rawTextExcerptLocation.firstCharacterPosition, 
                    seed.sourceSentence.rawTextExcerptLocation.lastCharacterPosition, 
                    seed) for seed in seedListIterator])
            for location, seedListIterator in groupby(seedSortedList, SeedingProcess.GetSuspiciousLocation)]

        # def detection area (indexes min max, i j)
        # cut off seeds in external detection area
        seedDetectedSet = set()
        for detection in detectionList:
            # solve border cases by threshold (cut off the ones failed)
            seedDetectedList = self.GetSeedListInDetection(
                seedMatrixLineSuspiciousColumnSource, 
                detection)
            # label remaing seed as detection.class
            for seed in seedDetectedList:
                seed.attributes.plagiarismClass = PlagiarismClass.FromPlagiarismObfuscation(detection.obfuscation)
            seedDetectedSet.update(seedDetectedList)
        return seedDetectedSet

    def SortSeedListBySuspiciousSourceLocation(self, seedList):
        return sorted(seedList, 
            key = lambda seed:
                (
                    SeedingProcess.GetSuspiciousLocation(seed)[0],
                    SeedingProcess.GetSourceLocation(seed)[0]))

    def GetSuspiciousLocation(seed):
        return (seed.suspiciousSentence.rawTextExcerptLocation.firstCharacterPosition,
            seed.suspiciousSentence.rawTextExcerptLocation.lastCharacterPosition)

    def GetSourceLocation(seed):
        return (seed.sourceSentence.rawTextExcerptLocation.firstCharacterPosition,
            seed.sourceSentence.rawTextExcerptLocation.lastCharacterPosition)

    def GetSeedListInDetection(self, seedMatrixLineSuspiciousColumnSource, detection):
        detectionSuspiciousFirstPosition = detection.rawTextSuspiciousLocation.firstCharacterPosition
        detectionSuspiciousLastPosition = detection.rawTextSuspiciousLocation.lastCharacterPosition
        detectionSourceFirstPosition = detection.rawTextSourceLocation.firstCharacterPosition
        detectionSourceLastPosition = detection.rawTextSourceLocation.lastCharacterPosition
        seedDetectedMatrix = [
            [seed 
                for sourceFirstPosition, sourceLastPosition, seed in suspiciousLine
                if(SeedingProcess.SentenceIsInDetection(
                    sourceFirstPosition, sourceLastPosition,
                    detectionSourceFirstPosition, detectionSourceLastPosition))]
            for suspiciousFirstPosition, suspiciousLastPosition, suspiciousLine in seedMatrixLineSuspiciousColumnSource
            if(SeedingProcess.SentenceIsInDetection(
                suspiciousFirstPosition, suspiciousLastPosition, 
                detectionSuspiciousFirstPosition, detectionSuspiciousLastPosition))]
        seedDetectedList = []
        [seedDetectedList.extend(seedList)
            for seedList in seedDetectedMatrix]
        return seedDetectedList

    def SentenceIsInDetection(sentenceFirstPosition, sentenceLastPosition, 
        detectionFirstPosition, detectionLastPosition):
        threshold = Threshold.DETECTION_MINIMUM_PERCENTUAL_INTERSECTION
        percentageInDetection = SeedingProcess.SentencePercentageInDetection(
            sentenceFirstPosition, sentenceLastPosition, detectionFirstPosition, detectionLastPosition)
        isIn = percentageInDetection > threshold
        return isIn
    
    def SentencePercentageInDetection(sentenceFirstPosition, sentenceLastPosition, 
        detectionFirstPosition, detectionLastPosition):
        sentenceLength = sentenceLastPosition - sentenceFirstPosition
        overlappedLength = min(detectionLastPosition, sentenceLastPosition) - max(detectionFirstPosition, sentenceFirstPosition)
        percentageInDetection = overlappedLength / sentenceLength
        return percentageInDetection
    #end_region [Fill seeds plagiarism class]    

    #region [Calculate attributes over seeds candidates]
    def CalculateAttributesSeeedList(self, seedingData, rawTextPairList):
        commitList = []
        for rawTextPair in rawTextPairList:
            seedList = self._seedRepository.GetListByRawTextPair(rawTextPair, seedingData)
            seedList = self.CalculateSeedListCosine(seedList)
            # seedList = self.CalculateDice(seedList)
            # seedList = self.CalculateIsMaxCosineDice(seedList)
            # seedList = self.CalculateMaxDiffCosineDice(seedList)
            # seedList = self.CalculateMeanDiffCosineDice(seedList)
            # seedList = self.CalculateMaxNeighbour(seedList)
            # seedList = self.CalculateVerticalMaxDistance(seedList)
            # seedList = self.CalculateLengthRatio(seedList)
            commitList.extend(seedList)
        self._baseRepository.InsertList(commitList)

    def CalculateSeedListCosine(self, seedList):
        for seed in seedList:  
            seed.attributes.cosine = SeedingProcess.Cosine(
                seed.suspiciousSentence.bagOfWords.wordOccurenceDictionary, 
                seed.sourceSentence.bagOfWords.wordOccurenceDictionary)
        return seedList

    def Cosine(dictionary1, dictionary2):
        scalarProduct = 0.0
        denominator =\
            SeedingProcess.EuclidianNormalize(dictionary1) *\
            SeedingProcess.EuclidianNormalize(dictionary2)
        if denominator == 0:
            return 0
        coocurrenceDicitionary = SeedingProcess.GetCoocurrenceDictionary(
            dictionary1, dictionary2)
        scalarProduct = sum([
            occurence1 * occurence2
            for occurence1, occurence2 in coocurrenceDicitionary.values()])
        cosine = scalarProduct/denominator
        return cosine
    
    def EuclidianNormalize(dictionary):
        squares = list(map(lambda value: value*value, dictionary.values()))
        _sum = sum(squares)
        euclidianNorm = math.sqrt(_sum)
        return euclidianNorm

    def GetCoocurrenceDictionary(dictionary1, dictionary2):
        keys1 = set(dictionary1.keys())
        keys2 = set(dictionary2.keys())
        commomKeys = keys1 & keys2
        coocurrenceDicitionary = {
            key: (dictionary1[key], dictionary2[key])
            for key in commomKeys}
        return coocurrenceDicitionary

def CalculateDice(seedList):
        pass

    def CalculateIsMaxCosineDice(seedList):
        pass

    def CalculateMaxDiffCosineDice(seedList):
        pass
        
    def CalculateMeanDiffCosineDice(seedList):
        pass

    def CalculateMaxNeighbour(seedList):
        pass

    def CalculateVerticalMaxDistance(seedList):
        pass

    def CalculateLengthRatio(seedList):
        pass
    #end_region [Calculate attributes over seeds candidates]
    
    _baseRepository = BaseRepository()
    _preProcessedDataRepository = PreProcessedDataRepository()
    _rawTextPairRepository = RawTextPairRepository()
    _sentenceListRepository = SentenceListRepository()
    _seedRepository = SeedRepository()
    _detectionRepository = DetectionRepository()
    _seedingDataRepository = SeedingDataRepository()

    def __init__(self):
        super().__init__()