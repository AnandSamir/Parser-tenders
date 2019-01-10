from bs4 import BeautifulSoup as BS
from src.bll import tools
from src.bll.http_worker import HttpWorker
from src.config import config
import requests
import re


class Parser:

    @classmethod
    def get_data_organization(cls):
        try:
            return config.customer_info_map
        except KeyError:
            return {"None": {"customer_inn": "", "customer_kpp": "", "customer_region": ""}}

    @classmethod
    def _parse_datetime_with_timezone(cls, datetime_str):
        return tools.convert_datetime_str_to_timestamp(datetime_str, config.platform_timezone)

    @classmethod
    def _get_attachments(cls, url):
        attachments = []
        html = HttpWorker.get_tenders(url).text
        soup = BS(html, 'lxml')
        trs = soup.find(text='Конкурсная документация').findNext('table').find_all('tr')[1:]
        for tr in trs:
            tds = tr.find_all('td')
            attachments.append({
                'displayName': tds[1].text.strip(),
                'href': '',
                'publicationDateTime': cls._parse_datetime_with_timezone(tds[2].text.strip()) * 1000,
                'realName': tds[1].text.strip(),
                'size': tds[3].text.strip(),
            })
        return attachments

    @classmethod
    def _get_lot(cls, name, url):
        lots = {'num': 1, 'name': name, 'url': url, 'price': 0, 'positions': [{'name': name}]}
        return [lots]

    @classmethod
    def _get_archive(cls, ts, next_url):
        t_data = cls.get_data_organization()
        html = HttpWorker.get_tenders(next_url).text
        soup = BS(html, 'lxml')
        while next_url:
            trs = soup.find('table', id='mytable').find_all('tr')[1:]
            for tr in trs:
                tender = {}
                tds = tr.find_all('td')
                tender['platform_href'] = 'https://tender.x5.ru'
                tender['tender_id'] = tds[0].text.strip()
                tender['tender_url'] = ''
                tender['tender_name'] = tds[1].text.strip()
                tender['tender_date_open'] = (cls._parse_datetime_with_timezone(tds[2].text.strip()) - 604800) * 1000
                tender['tender_date_publication'] = tender['tender_date_open']
                tender['tender_date_open_until'] = cls._parse_datetime_with_timezone(tds[2].text.strip()) * 1000
                tender['tender_placing_way'] = 0
                tender['tender_placing_way_human'] = ''
                tender['tender_price'] = 0
                tender['tender_contacts'] = []
                tender['tender_status'] = 3
                tender['tender_lots'] = cls._get_lot(tender.get('tender_name'), tender.get('tender_url'))
                tender['attachments'] = []
                tender['customer_name'] = next(iter(t_data.keys()))
                tender.update(t_data.get(tender['customer_name']))
                ts.append(tender)
            try:
                next_url = 'https://tender.x5.ru' + soup.find('div', id='MainCVS').form.find_all('table')[-1]\
                    .find_all('td')[-1].find('a').get('href')
            except:
                next_url = None
            yield ts

    @classmethod
    def parse_tenders(cls, html):
        tenders = []
        t_data = cls.get_data_organization()
        soup = BS(html, 'lxml')
        trs = soup.h2.nextSibling.nextSibling.find_all('tr')[1:]
        for tr in trs:
            tender = {}
            tds = tr.find_all('td')
            tender['platform_href'] = 'https://tender.x5.ru'
            tender['tender_id'] = tds[0].text.strip()
            tender['tender_url'] = 'https://tender.x5.ru' + tds[0].find('a').get('href')
            tender['tender_name'] = tds[1].text.strip()
            tender['tender_date_publication'] = cls._parse_datetime_with_timezone(tds[2].text.strip()) * 1000
            tender['tender_date_open'] = cls._parse_datetime_with_timezone(tds[3].text.strip()) * 1000
            tender['tender_date_open_until'] = cls._parse_datetime_with_timezone(tds[4].text.strip()) * 1000
            tender['tender_placing_way'] = 0
            tender['tender_placing_way_human'] = ''
            tender['tender_price'] = 0
            tender['tender_contacts'] = []
            tender['tender_status'] = 1
            tender['tender_lots'] = cls._get_lot(tender.get('tender_name'), tender.get('tender_url'))
            tender['attachments'] = cls._get_attachments(tender.get('tender_url'))
            tender['customer_name'] = next(iter(t_data.keys()))
            tender.update(t_data.get(tender['customer_name']))
            tenders.append(tender)

        return cls._get_archive(tenders, 'https://tender.x5.ru' + soup.find('a', class_='TextLink').get('href'))
