from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
 
Base = declarative_base()

class User(Base):
   __tablename__ = 'user'

   id = Column(Integer, primary_key = True)
   name = Column(String(250), nullable = False)
   email = Column(String(250))
   picture = Column(String(250))

   @property
   def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'id'           : self.id,
           'name'         : self.name,
           'email'         : self.email,
           'picture'         : self.picture,
       }


class Category(Base):
    __tablename__ = 'category'
   
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'name'         : self.name,
           'id'           : self.id,
	   'user_id'      : self.user_id
       }
 
class Item(Base):
    __tablename__ = 'item'


    name =Column(String(80), nullable = False)
    id = Column(Integer, primary_key = True)
    created_date = Column (DateTime, default=func.now())
    description = Column(String(250))
    price = Column(String(8))
    picture = Column(String(250))
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)
    category_id = Column(Integer,ForeignKey('category.id'))
    category = relationship(Category)


    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'name'         : self.name,
           'description'         : self.description,
           'id'         : self.id,
           'created_date': str(self.created_date),
           'price'         : self.price,
           'picture'       : self.picture,
           'category_id'   : self.category_id,
	   'user_id'      : self.user_id
       }


engine = create_engine('sqlite:///catalog.db')
 

Base.metadata.create_all(engine)
