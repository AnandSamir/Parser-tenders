import logging
import re

from lxml import html

from src.bll import tools
from src.config import config


class Parser:
    COMPANY_DETAILS = {
        'Группа Компаний ПИК': {'customer_inn': '7713011336', 'customer_kpp': '997450001', 'customer_region': '77'},
        'ПИК-Индустрия': {'customer_inn': '7729755852', 'customer_kpp': '774501001', 'customer_region': '77'},
        'ПИК-ЭЛЕМЕНТ': {'customer_inn': '9729159290', 'customer_kpp': '772901001', 'customer_region': '77'},
        'ООО "НСС"': {'customer_inn': '4025412892', 'customer_kpp': '402501001', 'customer_region': '40'},
        'ООО "480 КЖИ"': {'customer_inn': '7111021111', 'customer_kpp': '711101001', 'customer_region': '71'},
        'ЗАО "Волга-форм"': {'customer_inn': '5259030971', 'customer_kpp': '526301001', 'customer_region': '52'},
        'ООО "ПИК-Профиль"': {'customer_inn': '7713153394', 'customer_kpp': '772901001', 'customer_region': '77'},
        'ООО "ПИК-Комфорт"': {'customer_inn': '7701208190', 'customer_kpp': '770101001', 'customer_region': '77'},
        'АР "Энергосервис"': {'customer_inn': '7709571825', 'customer_kpp': '770301001', 'customer_region': '77'},
        'None': {'customer_inn': '', 'customer_kpp': '', 'customer_region': ''}
    }

    @classmethod
    def parse_tenders(cls, tenders_list):
        for tender in tenders_list:
            tender['tender_url'] = 'https://tender.pik.ru/tenders/' + tender['guid']
            t_data = cls.COMPANY_DETAILS.get(tender.get('requester_name'))
            tender.update(t_data) if t_data else tender.update(cls.COMPANY_DETAILS.get('None'))
            tender['tender_id'] = tender.pop('guid')
            tender['tender_name'] = tender.pop('name')
            tender['start_date'] = cls._parse_datetime_with_timezone(tender['start_date']) * 1000
            tender['tender_date_open'] = tender.pop('start_date')
            tender['tender_date_publication'] = tender.get('tender_date_open')
            tender['end_date'] = (cls._parse_datetime_with_timezone(tender['end_date']) + 60*60*24) * 1000
            tender['tender_date_open_until'] = tender.pop('end_date')
            tender['tender_status'] = 1 if tender['tender_date_open_until'] > tools.get_utc() else 3
            tender['customer_name'] = tender.pop('requester_name')
            tender['tender_placing_way_human'] = tender.pop('contact_name')
            tender['tender_price'] = ''
            tender['tender_lots'] = ''
            tender['tender_placing_way'] = ''

        return tenders_list

    @classmethod
    def _parse_datetime_with_timezone(cls, datetime_str):
        return tools.convert_datetime_str_to_timestamp(datetime_str + config.platform_timezone)
