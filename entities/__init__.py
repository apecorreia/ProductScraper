"""
This is the __init__.py file for the entities package.

Usage:
    from entities.product import ContinenteProduct, AuchanProduct, PingoDoceProduct - import the 3 entrities that define objects for the 3 stores
    
"""
from .product import Product, Store
from .db_registry import DBRegistry
