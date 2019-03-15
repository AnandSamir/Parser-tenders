from bs4 import BeautifulSoup as BS
from src.bll import tools
from src.bll.http_worker import HttpWorker
from src.config import config
import requests
import re


class Parser:

    STATUS = {
        'Неизвестно': 0,
        'Прием предложений': 1,
        'Согласование': 2,
        'Заключение договора': 3,
        'Договор заключен': 3,
        'Отменена': 4,
        'Нет предложений': 5,
        'Исполнение завершено': 6,
        'Исполняется': 7,
        'Расторжение': 8
    }

    @classmethod
    def _parse_datetime_with_timezone(cls, datetime_str):
        return tools.convert_datetime_str_to_timestamp(datetime_str, config.platform_timezone)

    @classmethod
    def _get_lot(cls, lot, url, price):
        lots = {'num': lot[0], 'name': lot[1], 'url': url, 'price': price,
                'positions': [{'name': lot[1], 'price': lot[4], 'unit': lot[2], 'number': lot[3], 'price_all': lot[5]}]}
        return [lots]

    @classmethod
    def _get_contacts(cls, info):
        contact = {}
        contact['name'] = info[0]
        contact['address'] = info[2]
        return contact

    @classmethod
    def _get_table(cls, url):
        lots, info, files = [], [], []
        details = HttpWorker.get_tenders(url).text
        soup = BS(details, 'lxml')
        it = soup.find_all('table', class_='info-table')
        tds = it[0].find_all('td') + it[1].find_all('td')
        key_words = ['Полное наименование', 'ИНН', 'Адрес места нахождения', 'Сроки поставки', 'Место поставки']
        for i in range(len(tds)):
            for word in key_words:
                if word in tds[i].text:
                    info += [tds[i+1].text.strip()]
                    break
        trs = soup.find_all('div', class_='collapsibleTab')[0].find_all('tr')[1:]
        num = 1
        for tr in trs:
            tds = tr.find_all('td')
            lots += [{0: num, 1: tds[1].text, 2: tds[3].text, 3: tds[4].text, 4: tds[5].text, 5: tds[6].text}]
            num += 1
        trs = it[1].find_all('tr')[1:]
        url_files = 'https://api.market.mosreg.ru/api/Trade/640652/GetTradeDocuments'
        files = HttpWorker.get_tenders_get(url_files).json()
        return lots, info, files

    @classmethod
    def parse_tenders(cls, html):
        tenders = []
        for t in html:
            url = 'https://market.mosreg.ru/Trade/ViewTrade?id=' + str(t.get('Id'))
            lots, info, files = cls._get_table(url)
            for lot in lots:
                tender = {}
                tender['tender_url'] = url
                tender['platform_href'] = 'https://market.mosreg.ru/'
                tender['tender_name'] = t.get('TradeName')
                tender['tender_id'] = t.get('Id')
                tender['tender_placing_way'] = 5000
                tender['tender_status'] = cls.STATUS[t.get('TradeStateName')]
                tender['customer_name'] = t.get('CustomerFullName')
                tender['tender_price'] = t.get('InitialPrice')
                date_pub = t.get('PublicationDate')
                date_close = t.get('FillingApplicationEndDate')
                tender['tender_date_publication'] = cls._parse_datetime_with_timezone(date_pub) * 1000
                tender['tender_date_open'] = cls._parse_datetime_with_timezone(date_pub) * 1000
                tender['tender_date_open_until'] = cls._parse_datetime_with_timezone(date_close) * 1000
                tender['tender_placing_way_human'] = ''
                tender['tender_contacts'] = [cls._get_contacts(info)]
                tender['tender_lots'] = cls._get_lot(lot, tender.get('tender_url'), tender['tender_price'])
                tender['customer_inn'] = info[0]
                tender['customer_kpp'] = ''
                tender['customer_region'] = info[0][:2]
                tenders.append(tender)

        return tenders
