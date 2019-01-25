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
        t_data = cls.get_data_organization()
        soup = BS(html, 'lxml')
        next_url = soup.find('table', class_='main_content_table').find('td', class_='mct_workarea') \
            .find('div', class_='page_navi_block').find('a', title='следующая страница')
        if not next_url:
            next_url = False
        lis = soup.find('table', class_='main_content_table').find('td', class_='mct_workarea')\
            .find_all('div', class_='tender_main_left')[1].find('ul', class_='tenders_list').find_all('li')
        for li in lis:
            tender = {}
            divs = li.find_all('div')
            tender['platform_href'] = 'http://sitno.ru/'
            tender['tender_name'] = divs[0].find('a').text.strip()
            tender['tender_id'] = divs[3].find_all('p')[0].contents[1].strip()
            tender['tender_url'] = 'http://sitno.ru/tender/index.php/' + divs[0].find('a').get('href')
            date_pub = divs[3].find_all('p')[1].contents[2].strip()
            date_close = divs[3].find_all('p')[2].contents[2].strip()
            tender['tender_date_publication'] = cls._parse_datetime_with_timezone(date_pub) * 1000
            tender['tender_date_open'] = cls._parse_datetime_with_timezone(date_pub) * 1000
            tender['tender_date_open_until'] = cls._parse_datetime_with_timezone(date_close) * 1000
            tender['tender_placing_way'] = 0
            tender['tender_placing_way_human'] = ''
            tender['tender_price'] = 0
            tender['tender_contacts'] = [cls._get_contacts(divs[2].find_all('p'))]
            tender['tender_status'] = 1 if tender['tender_date_open_until'] > tools.get_utc() else 3
            tender['tender_lots'] = cls._get_lot(tender.get('tender_name'), tender.get('tender_url'))
            tender['customer_name'] = divs[2].find_all('p')[1].contents[1].strip()
            c_data = t_data.get(tender['customer_name'])
            tender['customer_inn'] = c_data.get('inn')
            tender['customer_kpp'] = c_data.get('kpp')
            tender['customer_region'] = c_data.get('region')
            tenders.append(tender)

        return tenders, next_url
