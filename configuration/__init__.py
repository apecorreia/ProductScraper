"""
This is the __init__.py file for the configuration package.

Usage:
    from configuration.base import Base - import the object Base witch is one instance of the declarative_base object to create enteties
    from configuration.connection import DBConnectionHandler -  import class DBConnectionHandler to establish and handle interations with the database
"""
from .base import Base
from .connection import DBConnectionHandler
