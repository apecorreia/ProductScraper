"""
This module represents a class that will create some context when acessing the database.

"""

# Import of external modules
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Handler class
class DBConnectionHandler:
    '''This class handles the connections between the app and the database'''

    def __init__(self, database_url):

        # Initialize the url for the database
        self.__connection_string = database_url

        # Initialize the engine
        self.__engine = self.__create_database_engine()

    # Method to create the engine and return it
    def __create_database_engine(self):
        engine = create_engine(self.__connection_string)
        return engine


    def get_engine(self):
        """ 
        Method get to acess the engine value
        
        Returns the engine from an instance created
        """
        return self.__engine

    # Methods enter and exit for binding with the db
    def __enter__(self):

        create_session = sessionmaker(bind=self.__engine)
        self.session = create_session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
