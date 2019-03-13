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
    def _get_lot(cls, name, url):
        lots = {'num': 1, 'name': name, 'url': url, 'price': 0, 'positions': [{'name': name}]}
        return [lots]

    @classmethod
    def _get_contacts(cls, ps):
        re_email = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
        re_phone = r'[\+\(]?\b[\d\,\(\)\-\ ]+\b'
        phone = email = ''
        contact = {}
        contact['fio'] = ps[2].contents[1].strip()
        cont = re.search(re_phone, ps[3].contents[1])
        if cont:
            phone = cont.group().strip()
        cont = re.search(re_email, ps[3].contents[1])
        if cont:
            email = cont.group().strip()
        contact['phone'] = phone
        contact['email'] = email
        return contact

    @classmethod
    def parse_tenders(cls, html):
        tenders = []
        for t in html:
            tender = {}
            tender['tender_url'] = 'https://market.mosreg.ru/Trade/ViewTrade?id=' + str(t.get('Id'))

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

            tender['tender_contacts'] = [cls._get_contacts(divs[2].find_all('p'))]
            tender['tender_lots'] = cls._get_lot(tender.get('tender_name'), tender.get('tender_url'))
            tender['customer_inn'] = c_data.get('inn')
            tender['customer_kpp'] = ''
            tender['customer_region'] = c_data.get('region')
            tenders.append(tender)

        return tenders
