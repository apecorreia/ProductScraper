"""Script to un the project

Yields:
    CrawlerProcess: crawl spider
"""
import logging
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
#from scrapy.signals import spider_closed
from twisted.internet import defer

class SpiderRunner:
    """
    Class that initializes the crawl process
    
    Features:
    - Setting.py : uses custom settings to improve crawl process
    - Stats: saves stats to debbug and terminal info about the execution
    """
    def __init__(self):
        self.settings = get_project_settings()
        self.process = CrawlerProcess(self.settings)
        self.running_spiders = []
        self.stats = {}

    def spider_closed(self, spider):
        """Handler for spider closed signal"""
        spider_stats = spider.crawler.stats.get_stats()
        self.stats[spider.name] = {
            'items_scraped': spider_stats.get('item_scraped_count', 0),
            'runtime': spider_stats.get('finish_time') - spider_stats.get('start_time'),
            'finish_reason': spider_stats.get('finish_reason')
        }
        logging.info(f"Spider {spider.name} finished. Stats: {self.stats[spider.name]}") # pylint: disable=logging-fstring-interpolation

    @defer.inlineCallbacks
    def crawl(self):
        """
        Spiders crawl: Inicialize process of each spider on after the other

        Yields:
            CrawlerProcess: crawl spider
        """
        try:
            # Continente Spider
            logging.info("Starting Continente spider...")
            yield self.process.crawl('continente_spider')
            logging.info("Continente spider completed")

            # Pingo Doce Spider
            logging.info("Starting Pingo Doce spider...")
            yield self.process.crawl('pingo_doce_spider')
            logging.info("Pingo Doce spider completed")

            # Auchan Spider
            logging.info("Starting Auchan spider...")
            yield self.process.crawl('auchan_spider')
            logging.info("Auchan spider completed")

        except Exception as e: # pylint: disable=broad-exception-caught
            logging.error(f"Error during crawling: {str(e)}")# pylint: disable=logging-fstring-interpolation
        finally:
            self.process.stop()

    def run_spiders(self):
        """Main method to run all spiders sequentially"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler('spider_run.log'),
                logging.StreamHandler()
            ]
        )

        logging.info("Starting spider sequence...")

        self.crawl()
        self.process.start()

        # Print final statistics
        logging.info("All spiders completed. Final statistics:")
        for spider_name, stats in self.stats.items():
            logging.info(f"{spider_name}: {stats}")# pylint: disable=logging-fstring-interpolation
            print(f"{spider_name}: {stats}")

if __name__ == '__main__':
    runner = SpiderRunner()
    runner.run_spiders()
