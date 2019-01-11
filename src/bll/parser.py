from bs4 import BeautifulSoup as BS
from src.bll import tools
from src.bll.http_worker import HttpWorker
from src.config import config
import requests
import re


class Parser:

    CUSTOMER_TRANSLATE = {
        'Инн': 'customer_inn',
        'КПП': 'customer_kpp',
        'ОГРН': 'customer_ogrn',
        'Адрес': 'customer_address',
        'Телефон': 'customer_phone',
        'E-mail': 'customer_email'
    }
    CONTACTS_TRANSLATE = {
        'Адрес': 'address',
        'Телефон': 'phone',
        'E-mail': 'email'
    }

    @classmethod
    def _parse_datetime_with_timezone(cls, datetime_str):
        return tools.convert_datetime_str_to_timestamp(datetime_str, config.platform_timezone)

    @classmethod
    def _get_attachments(cls, att):
        attachments = []
        for _ in att:
            attachments.append({
                'displayName': _.a.text.strip(),
                'href': 'https://zakupki.roshneft.ru' + _.a.get('href'),
                'publicationDateTime': cls._parse_datetime_with_timezone(_.a.nextSibling.replace('- ', '').strip()) * 1000,
                'realName': _.a.text.strip(),
                'size': None,
            })
        return attachments

    @classmethod
    def _get_lot(cls, s_lots, lots, url):
        num = len(lots)
        for _ in s_lots:
            page_lot = requests.get(_.get('href')).text
            s = BS(page_lot, 'lxml')
            price = s.find('div', class_='info').text.strip()
            try:
                price = float(re.match(r'\d+[\d .]+\d+', price).group().replace(' ', ''))
            except:
                price = 0
            num += 1
            lots.append({'name': _.text.strip(), 'url': url, 'price': price, 'positions':
                         [{'num': num, 'name': _.text.strip(), 'url': _.get('href'), 'price': price}]})
        return lots

    @classmethod
    def _get_lots(cls, s_lots, url, soup):
        lots = cls._get_lot(s_lots, [], url)
        while True:
            pages_url = soup.find('div', class_='view-nodehierarchy-children-list').find('div', class_='item-list')
            try:
                p_url = pages_url.find('li', class_='pager-next').find('a').get('href')
            except:
                break
            html = requests.get(p_url).text
            soup = BS(html, 'lxml')
            s_lots = soup.find('div', class_='view-nodehierarchy-children-list').\
                find('div', class_='view-content').find_all('a')
            lots = cls._get_lot(s_lots, lots, p_url)

        return lots

    @classmethod
    def parse_tenders(cls, html):
        tenders, lots = [], []
        soup = BS(html, 'lxml')
        trs = soup.find('div', class_='view-content').find('table', class_='views-table').tbody.find_all('tr')
        for tr in trs:
            tds = tr.find_all('td')
            url = tds[1].find('a').get('href')
            html = HttpWorker.get_tenders(url).text
            if 'Ссылка на закупку на электронной торговой площадке' in html:
                continue
            soup = BS(html, 'lxml')
            s_lots = soup.find('div', class_='view-nodehierarchy-children-list').find('div', class_='view-content')
            if s_lots:
                s_lots = s_lots.find_all('a')
                lots = cls._get_lots(s_lots, url, soup)

            for lot in lots:
                tender = {}
                tender['tender_lots'] = [lot]
                tender['_platform_href'] = 'http://zakupki.rosneft.ru/'
                tender['tender_url'] = url
                tender['tender_name'] = tds[3].text.strip()
                pw = tds[4].text.strip()
                tender['tender_placing_way'] = pw == "Закупка у единственного поставщика" and 6 or\
                                               pw == 'Запрос предложений' and 14 or 0
                tender['tender_placing_way_human'] = ''
                try:
                    tender['tender_date_open'] = cls._parse_datetime_with_timezone(tds[5].text.strip()[:10]) * 1000
                    tender['tender_date_publication'] = tender.get('tender_date_open')
                except:
                    pass
                try:
                    tender['tender_date_open_until'] = (cls._parse_datetime_with_timezone(tds[6].text.strip()[:10]) + 86400) * 1000
                except:
                    pass
                tender['tender_id'] = tds[0].text.strip()
                trs2 = soup.find('table', class_='tender-table').tbody.find_all('tr')
                for tr2 in trs2:
                    if 'Организатор' == tr2.find('td', class_='cont-left').text.strip():
                        tender['customer_name'] = tr2.strong.text.strip()
                        c_info = tr2.div.contents
                        for i in range(3, len(c_info), 2):
                            kv = c_info[i].strip().split(': ')
                            if len(kv) == 2:
                                key, value = kv
                                tender[cls.CUSTOMER_TRANSLATE[key]] = value
                    if '(цене лота)' == tr2.find('td', class_='cont-left').text.strip()[-11:]:
                        price = tr2.find('div', class_='info').text.strip()
                        price = re.match(r'^[\d .]+\w+\b', price)
                        if price:
                            tender['tender_price'] = re.search(r'^[\d .]+\b', price.string).group().strip().replace(' ', '')
                            if tender['tender_price'].count('.') > 1:
                                tender['tender_price'] = float(tender['tender_price'].replace('.', '', count=1))
                            else:
                                tender['tender_price'] = float(tender['tender_price'])
                            currency = re.search(r'[а-яА-яA-Za-z]+', price.string)
                            if currency:
                                tender['tender_currency'] = currency.group()
                            else:
                                tender['tender_currency'] = 'руб'
                tender['tender_contacts'] = []
                for td in soup.find_all('td', class_='contact-left'):
                    c_info = td.nextSibling.nextSibling.find_all('div')
                    contact = {}
                    contact['fio'] = td.text.strip()
                    contact['address'] = td.text.strip()
                    contact['phone'] = td.text.strip()
                    contact['email'] = td.text.strip()
                    for c in c_info:
                        key, value = c.next.strip(), c.span.text.strip()
                        key = key.replace(':', '')
                        contact[cls.CONTACTS_TRANSLATE[key]] = value
                    tender['tender_contacts'].append(contact)
                att = soup.find('h2', text='Пакет документов').nextSibling.nextSibling.find_all('div')
                tender['attachments'] = cls._get_attachments(att)
                if 'последние изменения' in html:
                    ind = html.find('последние изменения от') + 23
                    tender['tender_modDateTime'] = cls._parse_datetime_with_timezone(html[ind:ind + 10]) * 1000
                status = soup.find('div', class_='tender-date').find_all('strong')[-1].text.strip()[18:]
                tender['tender_status'] = (status == 'Архив' and 3) or (status == 'Активные' and 1)

                tenders.append(tender)

        return tenders
