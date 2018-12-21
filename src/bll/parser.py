import logging
import re

from lxml import html

from src.bll import tools
from src.config import config


class Parser:
    COMPANY_DETAILS = {
        'Группа Компаний ПИК': {'inn': '7713011336', 'kpp': '997450001', 'region': '77'},
        'ПИК-Индустрия': {'inn': '7729755852', 'kpp': '774501001', 'region': '77'},
        'ПИК-ЭЛЕМЕНТ': {'inn': '9729159290', 'kpp': '772901001', 'region': '77'},
        'ООО "НСС"': {'inn': '4025412892', 'kpp': '402501001', 'region': '40'},
        'ООО "480 КЖИ"': {'inn': '7111021111', 'kpp': '711101001', 'region': '71'},
        'ЗАО "Волга-форм"': {'inn': '5259030971', 'kpp': '526301001', 'region': '52'},
        'ООО "ПИК-Профиль"': {'inn': '7713153394', 'kpp': '772901001', 'region': '77'},
        'ООО "ПИК-Комфорт"': {'inn': '7701208190', 'kpp': '770101001', 'region': '77'},
        'АР "Энергосервис"': {'inn': '7709571825', 'kpp': '770301001', 'region': '77'},
        'None': {'inn': '', 'kpp': '', 'region': ''}
    }

    @classmethod
    def parse_tenders(cls, tenders_list):
        for tender in tenders_list:
            tender['t_url'] = 'https://tender.pik.ru/tenders/' + tender['guid']
            t_data = cls.COMPANY_DETAILS.get(tender.get('requester_name'))
            tender.update(t_data) if t_data else tender.update(cls.COMPANY_DETAILS.get('None'))
            tender['t_id'] = tender.pop('guid')
            tender['t_name'] = tender.pop('name')
            tender['start_date'] = cls._parse_datetime_with_timezone(tender['start_date'])
            tender['t_date_open'] = tender.pop('start_date')
            tender['t_date_pub'] = tender('t_date_open')
            tender['end_date'] = cls._parse_datetime_with_timezone(tender['end_date']) + 60*60*24
            tender['t_date_close'] = tender.pop('end_date')
            tender['t_status'] = 1 if tender['t_date_close'] > tools.get_utc() else 3
            tender['c_name'] = tender.pop('requester_name')
            tender['t_placing_way_human'] = tender.pop('contact_name')

            # self.tender_price = t_price
            # self.tender_lots = lots
            # self.tender_placing_way = t_placing_way
        return tenders_list

    @classmethod
    def parse_tender_gen(cls, tender_html_raw, dt_open):
        lots_gen = None
        tender_html = html.fromstring(tender_html_raw)
        lots_element = tender_html.xpath("//tr[@id='MainContent_carTabPage_TrLotPage2']")
        date_close_raw = tender_html.xpath("//span[@id='MainContent_carTabPage_txtBiddingEndDate']")
        price_raw = tender_html.xpath("//a[@id='MainContent_carTabPage_txtStartSumm']")
        price = float(price_raw[0].text.replace(',', '.').replace('\xa0', '')) if price_raw and price_raw[0].text \
            else None
        date_close = cls._parse_datetime_with_timezone(date_close_raw[0].text) if date_close_raw and date_close_raw[
            0].text else dt_open
        if date_close:
            status = 1 if date_close > tools.get_utc() else 3
        else:
            status = 3
        if lots_element:
            lots_trs = lots_element[0].xpath("td/table/tr[not(@class='DataGrid_HeaderStyle')]")
            lots_gen = cls._parse_lots_gen(lots_trs)
        yield status, price, date_close, lots_gen

    @classmethod
    def _parse_datetime_with_timezone(cls, datetime_str):
        return tools.convert_datetime_str_to_timestamp(datetime_str + config.platform_timezone)
