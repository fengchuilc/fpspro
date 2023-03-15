import html
import json
import random
import re
import time

import scrapy
from scrapy import Selector, Request
from scrapy.linkextractors import LinkExtractor
from scrapy.linkextractors.lxmlhtml import LxmlLinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from scrapy_redis.spiders import RedisCrawlSpider

from fpspro.items import NewsItem, BodyItem


def ListCombiner(lst):
    string = ""
    for e in lst:
        string += e
    return string.replace(' ','').replace('\n','').replace('\t','')\
        .replace('\xa0','').replace('\u3000','').replace('\r','')\
        .replace('[]','')

class FbsSpider(RedisCrawlSpider):
    name = 'fps'
    # start_urls = ['https://news.163.com',
    #               ]
    redis_key = "fps:start_urls"
    # http://news.163.com/17/0823/20/CSI5PH3Q000189FH.html

    url_pattern = r'https://www\.163\.com/\w+/article/(\w+)\.html'

    rules = [
        Rule(LxmlLinkExtractor(allow=[url_pattern]), callback='parse_news', follow=True)
    ]

    def parse_news(self, response):
        ran = random.randint(1, 30)
        if ran == 1:
            time.sleep(3)
        sel = Selector(response)
        pattern = re.match(self.url_pattern, str(response.url))
        source = 'netease'
        if response.css('.post_body'):
            body = html.unescape(response.css('.post_body').extract()[0])
        else:
            body = 'null'
        if response.css('.post_info'):
            time_ = response.css('.post_info').extract()[0].split()[2] + '  ' + \
                    response.css('.post_info').extract()[0].split()[3]
            # time_ = response.css('.post_info').extract()[1].split()[0]+' '+response.css('.post_info').extract()[1].split()[1]
        else:
            time_ = 'unknown'
        newsId = pattern.group(1)
        url = response.url
        title = response.css('h1::text').extract()[0]
        # title = sel.xpath('//*[@id="container"]/div[1]/h1/text()').extract()[0]
        contents = ListCombiner(sel.xpath('//p/text()').extract()[2:-3])
        comment_url = 'http://comment.news.163.com/api/v1/products/a2869674571f77b5a0867c3d71db5856/threads/{}'.format(
            newsId)
        yield Request(comment_url, self.parse_comment, meta={'source': source,
                                                             'newsId': newsId,
                                                             'url': url,
                                                             'title': title,
                                                             'contents': contents,
                                                             'time': time_,
                                                             'body': body
                                                             }, dont_filter=True)

    def parse_comment(self, response):
        result = json.loads(response.text)
        item = NewsItem()
        body = BodyItem()
        body['body'] = response.meta['body']
        body['time'] = response.meta['time']
        body['source'] = response.meta['source']
        body['newsId'] = response.meta['newsId']
        yield body
        item['source'] = response.meta['source']
        item['newsId'] = response.meta['newsId']
        item['url'] = response.meta['url']
        item['title'] = response.meta['title']
        item['contents'] = response.meta['contents']
        item['comments'] = result['cmtAgainst'] + result['cmtVote'] + result['rcount']
        item['time'] = response.meta['time']
        yield item
