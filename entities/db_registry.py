
from sqlalchemy import String, Column, Integer, Integer
from configuration.base import Base

class DBRegistry(Base):
    
    __tablename__ = 'register'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    creation_date = Column(String, nullable=False)
    creation_time = Column(String, nullable=False)
    run_time = Column(String, nullable=True)
    scraped_items = Column(Integer, nullable=False)
    products_count = Column(Integer, nullable=False)
    db_url = Column(String, nullable=False)
    