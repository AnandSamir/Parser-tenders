import logging
import re

from lxml import html

from src.bll import tools
from src.config import config


class Parser:

    @classmethod
    def get_data_organization(cls):
        try:
            return config.customer_info_map
        except KeyError:
            return {"None": {"customer_inn": "", "customer_kpp": "", "customer_region": ""}}

    @classmethod
    def _parse_datetime_with_timezone(cls, datetime_str):
        return tools.convert_datetime_str_to_timestamp(datetime_str + config.platform_timezone)

    @classmethod
    def _get_attachments(cls, docs, pub_date):
        attachments = []
        attachments.append({
            'displayName': docs.get('name'),
            'href': docs.get('ref'),
            'publicationDateTime': pub_date,
            'realName': docs.get('name'),
            'size': None,
        })
        return attachments

    @classmethod
    def parse_tenders(cls, tenders_list):
        t_data = cls.get_data_organization()
        for tender in tenders_list:
            tender.update(t_data.get(tender.get('requester_name')))
            tender['tender_url'] = 'https://tender.pik.ru/tenders/' + tender['guid']
            tender['tender_id'] = tender.pop('guid')
            tender['tender_name'] = tender.pop('name')
            tender['tender_date_open'] = cls._parse_datetime_with_timezone(tender['start_date']) * 1000
            tender['tender_date_publication'] = tender.get('tender_date_open')
            tender['tender_date_open_until'] = (cls._parse_datetime_with_timezone(tender['end_date']) + 60*60*24) * 1000
            tender['tender_status'] = 1 if tender['tender_date_open_until'] > tools.get_utc() else 3
            tender['_customer_guid'] = tender.pop('requester_id')
            tender['customer_name'] = tender.pop('requester_name')
            if tender.get('docs'):
                tender['attachments'] = cls._get_attachments(tender.get('docs')[0], tender.get('tender_date_publication'))
            tender['tender_price'] = 0
            tender['tender_placing_way'] = 0
            tender['tender_placing_way_human'] = ''
            contacts = []
            contacts.append({
                'fio': tender.pop('contact_name'),
                'phone': '',
                'email': ''
            })
            tender['tender_contacts'] = contacts
            lot = []
            lot.append({
                'num': 1,
                'name': tender.get('tender_name', None),
                'url': tender.get('tender_url', None),
                'quantity': None,
                'price': 0,
                'positions': [{
                    'name': tender.get('tender_name', None),
                    'quantity': None
                }]
            })
            tender['tender_lots'] = lot

            list_del = ['type', 'service_name', 'docs', 'owner', 'start_date', 'end_date']
            [tender.pop(key, None) for key in list_del]

        return tenders_list
