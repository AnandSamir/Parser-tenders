from bs4 import BeautifulSoup as BS
from src.bll import tools
from src.config import config
import requests


class Parser:

    @classmethod
    def _parse_datetime_with_timezone(cls, datetime_str):
        return tools.convert_datetime_str_to_timestamp(datetime_str, config.platform_timezone)

    @classmethod
    def _get_attachments(cls, url):
        attachments = []
        tender_page = requests.get(url).text
        soup_tender = BS(tender_page, 'lxml')
        try:
            tds = soup_tender.find_all('div', class_='content')[2].table.find_all('td', class_=['date', 'comment'])
        except:
            tds = []
        for _ in range(0, len(tds), 2):
            attachments.append({
                'displayName': tds[_+1].text,
                'href': 'https://zakupki.bashneft.ru' + tds[_+1].find('a').get('href'),
                'publicationDateTime': cls._parse_datetime_with_timezone(tds[_].text) * 1000,
                'realName': tds[_+1].text,
                'size': None,
            })
        return attachments

    @classmethod
    def _get_lot(cls, name, url):
        lot = []
        lot.append({'num': 1, 'name': name, 'url': url, 'quantity': None, 'price': 0,
                    'positions': [{'name': name, 'quantity': None}]})
        return lot

    @classmethod
    def parse_tenders(cls, html):
        tenders = []
        soup = BS(html, 'lxml')
        trs = soup.find('div', id='div_pager_items').find_all('tr')[3:]
        for tr in trs:
            tender = {}
            td = tr.find_all('td')
            tender['tender_date_open'] = cls._parse_datetime_with_timezone(td[0].find('a').text) * 1000
            tender['tender_date_publication'] = tender.get('tender_date_open')
            tender['tender_date_open_until'] = (cls._parse_datetime_with_timezone(td[1].find('a').text) + 86400) * 1000
            tender['tender_name'] = td[6].text
            tender['tender_placing_way'] = 5000
            tender['tender_placing_way_human'] = ''
            tender['customer_name'] = td[4].text
            tender['_platform_href'] = 'https://zakupki.bashneft.ru/'
            tender['tender_url'] = 'https://zakupki.bashneft.ru/' + td[0].find('a').get('href')
            tender['tender_id'] = td[5].text
            tender['tender_price'] = 0
            tender['attachments'] = cls._get_attachments(tender['tender_url'])
            tender['tender_status'] = 1 if tender['tender_date_open_until'] > tools.get_utc() else 3
            tender['tender_lots'] = cls._get_lot(tender.get('tender_name'), tender.get('tender_url'))

            tenders.append(tender)

        return tenders
