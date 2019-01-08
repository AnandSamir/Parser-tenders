import logging
from copy import copy

import src.bll.tools as tools
from sharedmodel.module import Root, Field, Customer
from sharedmodel.module.enum import FieldType, Modification
from sharedmodel.module.table import Head, Cell
from src.config import config


class Mapper:
    platform_name = 'Роснефть закупки'
    _platform_href = None
    _tender_short_model = None
    _customer_guid = None
    tender_id = None
    tender_name = None
    tender_price = None
    tender_url = None
    tender_date_publication = None
    tender_date_open_until = None
    tender_date_open = None
    tender_lots = None
    tender_status = None
    tender_placing_way = None
    tender_placing_way_human = None
    customer_name = None
    customer_region = None
    customer_inn = None
    customer_kpp = None
    customer_ogrn = None
    customer_address = None
    customer_phone = None
    customer_email = None
    attachments = None
    tender_contacts = None
    tender_currency = None
    tender_modDateTime = None

    def __init__(self, id_, status, http_worker):
        """

        Args:
            id_(int): Ид тендера
            status(int): Статус тендера
            http_worker:
        """
        self.logger = logging.getLogger(
            '{}.{}'.format(config.app_id, 'mapper'))
        self.tender_id = id_
        self.tender_status = status
        self.http = http_worker

    @property
    def tender_short_model(self):
        if not self._tender_short_model:
            self._tender_short_model = {'_id': str(
                self.tender_id), 'status': self.tender_status}
        return self._tender_short_model

    def tender_model_gen(self):
        yield from self._map_gen(one=False if self.tender_lots else True)

    def get_shared_model(self, lot=None):
        shared_model = Root()
        # в данном блоке должны присутствовать maxPrice, guaranteeApp, guaranteeContract
        # Основной блок
        shared_model.add_general(
            lambda f: f.set_properties(
                name='Currency',
                displayName='Валюта',
                value=self.tender_currency,
                type=FieldType.String,
                modifications=[]
            )
        )
        # блок заказчика
        shared_model.add_customer(
            Customer().set_properties(
                max_price=lot['price'] if lot else self.tender_price,
                guarantee_app=None,
                guarantee_contract=None,
                customer_guid=self.customer_guid,
                customer_name=self.customer_name
            ))
        # информация о закупке
        shared_model.add_category(
            lambda c: c.set_properties(
                name='ObjectInfo',
                displayName='Информация о объекте закупки'
            ).add_field(Field(
                name='TenderName',
                displayName='Наименование тендера',
                value=self.tender_name,
                type=FieldType.String
            ))
        )
        # информация о лотах
        if lot and 'positions' in lot:
            shared_model.add_category(
                lambda c: c.set_properties(
                    name='ObjectLots',
                    displayName='Лоты'
                ).add_table(
                    lambda t: t.set_properties(
                        name='Objects',
                        displayName='Лоты'
                    ).set_header(
                        lambda th: th.add_cells([
                            Head(name='Name', displayName='Наименование'),
                            Head(name='Price', displayName='Стоимость')
                        ])
                    ).add_rows(
                        lot['positions'],
                        lambda elem, row: row.add_cells([
                            Cell(
                                name='Name',
                                type=FieldType.String,
                                value=elem['name']
                            ),
                            Cell(
                                name='Price',
                                type=FieldType.Price,
                                value=elem['price']
                            )
                        ])
                    )
                )
            )
        # блок данных о заказе (в основном даты и места)
        shared_model.add_category(
            lambda c: c.set_properties(
                name='ProcedureInfo',
                displayName='Порядок размещения заказа'
            ).add_field(Field(
                name='SubmissionStartDateTime',
                displayName='Дата начал приема заявок',
                value=self.tender_date_open,
                type=FieldType.DateTime
            )).add_field(Field(
                name='SubmissionCloseDateTime',
                displayName='Дата окончания приема заявок',
                value=self.tender_date_open_until,
                type=FieldType.DateTime
            )).add_field(Field(
                name='biddingDateTime',
                displayName='Дата проведения торгов',
                value=self.tender_date_open,
                type=FieldType.DateTime
            ))
        )
        # блок контактов и данных об организаторе
        shared_model.add_category(
            lambda c: c.set_properties(
                name='Contacts',
                displayName='Контактная информация',
                modifications=[]
            ).add_field(Field(
                name='Organization',
                displayName='Организация',
                value=self.customer_name,
                type=FieldType.String,
                modifications=[]
            )
            ).add_array(
                lambda c: c.set_properties(
                    name='Contacts',
                    displayName='Контакты',
                    modifications=[Modification.HiddenLabel]
                ).add_array_items(
                    self.tender_contacts,  # list
                    lambda item, index: c.add_field(Field(
                        name='FIO' + str(index),
                        displayName='ФИО',
                        value=item['fio'],
                        type=FieldType.String,
                        modifications=[Modification.HiddenLabel]
                    )
                    ).add_field(Field(
                        name='Address' + str(index),
                        displayName='Адрес',
                        value=item['address'],
                        type=FieldType.String,
                        modifications=[]
                    )
                    ).add_field(Field(
                        name='Phone' + str(index),
                        displayName='Телефон',
                        value=item['phone'],
                        type=FieldType.String,
                        modifications=[]
                    )
                    ).add_field(Field(
                        name='Email' + str(index),
                        displayName='Электронная почта',
                        value=item['email'],
                        type=FieldType.String,
                        modifications=[Modification.Email]
                    )
                    )
                )
            )
        )
        return shared_model.to_json()

    def _map_gen(self, one=False):
        model = {
            # заказчики
            'customers': [{'guid': self.customer_guid, 'name': self.customer_name, 'region': self.customer_region}],
            # обеспечение заявки
            'guaranteeApp': None,
            # обеспечение контракта
            'guaranteeContract': None,
            # ссылка на тендер (лот)
            'href': self.tender_url,
            # Тендер - 0, план-график - 1
            # На большинстве площадок только тендеры, поэтому оставить 0
            # Если модель - план график, то 1
            'kind': 0,
            # Номер тендера (как в id, только без лота)
            'number': str(self.tender_id),
            # Массив ОКПД (если присутствует) ex. ['11.11', '20.2']
            'okpd': [],
            # Массив ОКПД2 (если присутствует)
            'okpd2': [],
            # Массив ОКДП (если присутствует)
            'okdp': [],
            # Статус тендера
            'status': self.tender_status,
            # TODO добавить self.customer_guid - сейчас заглушка
            # Строка для поиска организаций, customers+participants (Название организации ИНН КПП GUID)
            'organisationsSearch': ' '.join(
                (self.customer_name, str(self.customer_inn) if self.customer_inn else '',
                 str(self.customer_kpp) if self.customer_kpp else '')),
            # Способ определения поставщика
            'placingWay': self.tender_placing_way,
            # Ссылка на площадку (ссылка, название)
            'platform': {'href': self._platform_href, 'name': self.platform_name},
            # Дата публикации тендера UNIX EPOCH (UTC)
            'publicationDateTime': self.tender_date_publication,
            # Регион тендера (если нет явного, берем по региону заказчика)
            'region': self.customer_region,
            # Дата начала подачи заявок UNIX EPOCH (UTC)
            'submissionStartDateTime': self.tender_date_open,
            # Дата окончания подачи заявок UNIX EPOCH (UTC)
            'submissionCloseDateTime': self.tender_date_open_until,
            # Дата проведения аукциона в электронной форме (если есть) UNIX EPOCH (UTC)
            'biddingDateTime': self.tender_date_open,
            # Дата маппинга модели в UNIX EPOCH (UTC) (milliseconds)
            'timestamp': tools.get_utc(),
            # Тип парсера (можно не менять)
            'type': 30,
            # Версия извещения
            # Если на площадке нет версии, то ставить 1
            'version': 1,
            # Прикрепленные документы (массив)
            'attachments': self.attachments,
            # Дата изменения тендера
            'modDateTime': self.tender_modDateTime
        }
        if not one:
            for lot_num, lot in enumerate(self.tender_lots):
                lot_model = copy(model)
                lot_model.update({
                    'id': '{}_{}'.format(self.tender_id, lot_num + 1),
                    'globalSearch': ' '.join((self.tender_name, str(self.tender_id), lot['name'],
                                              *[p['name'] for p in lot['positions']], self.tender_placing_way_human)),
                    'json': self.get_shared_model(lot),
                    'maxPrice': lot['price'],
                    'multilot': len(self.tender_lots) > 1,
                    'tenderSearch': ' '.join(
                        (self.tender_name, str(self.tender_id), lot['name'], *[p['name'] for p in lot['positions']])),
                })
                yield lot_model
        else:
            model.update({
                'id': '{}_{}'.format(self.tender_id, 1),
                'globalSearch': ' '.join((self.tender_name, str(self.tender_id), self.tender_placing_way_human)),
                'json': self.get_shared_model(),
                'maxPrice': self.tender_price,
                'multilot': False,
                'tenderSearch': ' '.join((self.tender_name, str(self.tender_id))),
            })
            yield model

    @property
    def customer_guid(self):
        if not self._customer_guid:
            self._customer_guid = ''
        return self._customer_guid

    def load_customer_info(self, customer_name):
        org_info = self.http.get_organization(
            customer_name, self.customer_inn, self.customer_kpp)
        if org_info['name']:
            self.customer_name = org_info['name']
        else:
            self.customer_name = customer_name
        if org_info['region']:
            self.customer_region = org_info['region']
        else:
            try:
                self.customer_region = int(
                    str(config.customer_info_map[customer_name]['inn'])[:2])
            except KeyError:
                self.logger.error(
                    'can`t find customer {} in customer map'.format(customer_name))
                self.customer_region = None
                self.customer_inn = None
                self.customer_kpp = None
                return self
        self.customer_inn = str(config.customer_info_map[customer_name]['inn'])
        self.customer_kpp = str(config.customer_info_map[customer_name]['kpp'])
        return self

    def load_tender_info(self, **kwargs):
        for k in kwargs:
            setattr(self, k, kwargs[k])
        return self
