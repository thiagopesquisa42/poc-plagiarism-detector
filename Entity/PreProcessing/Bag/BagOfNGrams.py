from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from Entity import _EntityBase as EntityBase

class BagOfNGrams(EntityBase):
    __tablename__               = 'bag_of_n_grams'
    id                          = Column(Integer, primary_key=True, nullable=False, autoincrement=True)
    rawTextExcerptLocationId    = Column(Integer, ForeignKey('raw_text_excerpt_location.id'), nullable=False)
    rawTextExcerptLocation      = relationship('RawTextExcerptLocation', foreign_keys=[rawTextExcerptLocationId])
    
    #unique identifier of the object
    def __repr__(self):
        return "<BagOfNGrams (id='" + id + "'>"
