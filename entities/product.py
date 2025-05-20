from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, Numeric, Boolean
from sqlalchemy.orm import relationship

from configuration.base import Base

class Store(Base):
    __tablename__ = 'stores'

    storeId = Column(Integer, primary_key=True, autoincrement=True)
    storeName = Column(String, nullable=False, unique=True)

    # Relationship with Product
    products = relationship("Product", back_populates="store", cascade="all, delete-orphan")

class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True, autoincrement=True)
    storeId = Column(Integer, ForeignKey('stores.storeId', ondelete="CASCADE"), nullable=False)
    category = Column(Text, nullable=False)
    sub_category = Column(Text, nullable=True)
    name = Column(Text, nullable=False)
    brand = Column(Text, nullable=True)
    quantity = Column(Text, nullable=True)
    quantity_value = Column(Numeric(20,3))
    quantity_unit = Column(String)
    quantity_items = Column(Integer)
    quantity_total = Column(Numeric(20,3))
    primaryPrice = Column(Float, nullable=False)
    primaryPriceUnit = Column(Text, nullable=True)
    beforeDiscountPrice = Column(Float, nullable=True)
    hasDiscount = Column(Boolean, nullable = False, default=0)
    secondaryPrice = Column(Float, nullable=True)
    secondaryPriceUnit = Column(Text, nullable=True)
    image = Column(Text, nullable=True)

    # Relationship with Store
    store = relationship("Store", back_populates="products")