"""
Spider middlewares

Features:
    - ScraperSpiderMiddleware class with the default settings
    - ScraperDownloaderMiddleware class with the defaults settings, it hooks into Scrapy's requests
and responses and allow the spider to alter between them
    - ScrapeOpsFakeUserAgentMiddleware class that uses a ScrapeOps API to generate fake UserAgents 
and Headers in order to avoid being blocked by the target url
"""
import random
from urllib.parse import urlencode
import requests

from scrapy import signals

class ScraperSpiderMiddleware:
    """
    Not all methods need to be defined. If a method is not defined, scrapy acts as if the spider
    middleware does not modify the passed objects
    """

    @classmethod
    def from_crawler(cls, crawler):
        """This method is used by Scrapy to create your spiders.
        """
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider): # pylint: disable=unused-argument
        """Called for each response that goes through the spider middleware and into the spider.
        
        Returns:
            Should return None or raise an exception.      
        """
        return None

    def process_spider_output(self, response, result, spider):# pylint: disable=unused-argument
        """Called with the results returned from the Spider, after it has processed the response
        
        Args:
            response (response)
            spider (spider)

        Yields:
            request: iterable of Request, or item objects
        """
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        """
        Called when a spider or process_spider_input() method (from other spider middleware) raises
        an exception.

        Should return either None or an iterable of Request or item objects.
        """
        pass # pylint: disable=unnecessary-pass

    def process_start_requests(self, start_requests, spider):# pylint: disable=unused-argument
        """
        Called with the start requests of the spider, and works similarly to the
        process_spider_output() method, except that it doesn’t have a response associated.

        Must return only requests (not items).
        """
        for r in start_requests:
            yield r

    def spider_opened(self, spider):
        """
        Log on initialize
        """

        spider.logger.info(f"Spider opened: {spider.name}")


class ScraperDownloaderMiddleware:
    """
    Not all methods need to be defined. If a method is not defined, scrapy acts as if the
downloader middleware does not modify the passed objects.
    """
    @classmethod
    def from_crawler(cls, crawler):
        """This method is used by Scrapy to create your spiders.
        """
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_request(self, request, spider):# pylint: disable=unused-argument
        """
        Called for each request that goes through the downloader middleware.
        Must either:

        - return None: continue processing this request
        - or return a Response object
        - or return a Request object
        - or raise IgnoreRequest: process_exception() methods of
          installed downloader middleware will be called
        """
        return None

    def process_response(self, request, response, spider):# pylint: disable=unused-argument
        """
        Called with the response returned from the downloader.

        Must either;
        - return a Response object
        - return a Request object
        - or raise IgnoreRequest
        """
        return response

    def process_exception(self, request, exception, spider):
        """
        Called when a download handler or a process_request() (from other downloader middleware)
        raises an exception.

        Must either:
        - return None: continue processing this exception
        - return a Response object: stops process_exception() chain
        - return a Request object: stops process_exception() chain
        """
        pass # pylint: disable=unnecessary-pass

    def spider_opened(self, spider):
        """Log on initialize
        """
        spider.logger.info(f"Spider opened: {spider.name}")

class ScrapeOpsFakeUserAgentMiddleware:
    """
    Custom Middleware to Fetch Fake User Agents and Headers from ScrapeOps API

    Returns:
        list: List of fake user agents fetch from scrapeOps API
    """
    @classmethod
    def from_crawler(cls, crawler):
        """
        Fetch settings from spider

        Returns:
            cls: spider settings
        """
        return cls(crawler.settings)

    def __init__(self, settings):
        self.scrapeops_api_key = settings.get('SCRAPEOPS_API_KEY')
        self.scrapeops_endpoint = settings.get('SCRAPEOPS_FAKE_USER_AGENT_ENDPOINT',
                                               'http://headers.scrapeops.io/v1/user-agents?')
        self.scrapeops_fake_user_agents_active = settings.get('SCRAPEOPS_FAKE_USER_AGENT_ENABLED',
                                                              False)
        self.scrapeops_num_results = settings.get('SCRAPEOPS_NUM_RESULTS')
        self.headers_list = []
        self._get_user_agents_list()
        self._scrapeops_fake_user_agents_enabled()

    def _get_user_agents_list(self):
        payload = {'api_key': self.scrapeops_api_key}
        if self.scrapeops_num_results is not None:
            payload['num_results'] = self.scrapeops_num_results
        response = requests.get(self.scrapeops_endpoint, params=urlencode(payload)) # pylint: disable=missing-timeout
        json_response = response.json()
        self.user_agents_list = json_response.get('result', [])

    def _get_random_user_agent(self):
        random_index = random.randint(0, len(self.user_agents_list) - 1)
        return self.user_agents_list[random_index]

    def _scrapeops_fake_user_agents_enabled(self):
        if self.scrapeops_api_key is None or self.scrapeops_api_key == '' or self.scrapeops_fake_user_agents_active == False: # pylint: disable=singleton-comparison,line-too-long
            self.scrapeops_fake_user_agents_active = False
        self.scrapeops_fake_user_agents_active = True

    def process_request(self, request, spider): # pylint: disable=unused-argument
        """
        Process the request from spider calling the _get_random_user_agent()

        Args:
            request (request): request to url
            spider (spider): project active spider
        """
        random_user_agent = self._get_random_user_agent()
        request.headers['User-Agent'] = random_user_agent
