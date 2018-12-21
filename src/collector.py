import logging

from src.bll.http_worker import HttpWorker
from src.bll.mapper import Mapper
from src.bll.parser import Parser
from src.config import config
from src.repository.mongodb import MongoRepository
from src.repository.rabbitmq import RabbitMqProvider


class Collector:
    __slots__ = ['logger', '_repository', '_rabbitmq']

    def __init__(self):
        self.logger = logging.getLogger('{}.{}'.format(config.app_id, 'collector'))
        self._repository = None
        self._rabbitmq = None

    @property
    def repository(self):
        if not self._repository:
            self._repository = MongoRepository(config.mongo['host'], config.mongo['port'], config.mongo['database'],
                                               config.mongo['collection'])
        return self._repository

    @property
    def rabbitmq(self):
        if not self._rabbitmq:
            self._rabbitmq = RabbitMqProvider(config.rabbitmq['host'], config.rabbitmq['port'],
                                              config.rabbitmq['username'], config.rabbitmq['password'],
                                              config.rabbitmq['queue'])
        return self._rabbitmq

    def tender_list_gen(self):
        tender_list = HttpWorker.get_tenders_list().json()['data']
        tender_list_up = Parser.parse_tenders(tender_list)
        for x in tender_list_up:
            if not x['requester_name']:
                continue

            self.logger.info('[tender-{}] PARSING STARTED'.format(t_url))
            # res = self.repository.get_one(x['guid'])
            # if res and res['status'] == 3:
            #     self.logger.info('[tender-{}] ALREADY EXIST'.format(t_url))
            #     continue

            mapper = Mapper(id_=x['guid'], status=tender['status'], http_worker=HttpWorker)
            mapper.load_tender_info(t_id, t_status, t_name, t_price, t_pway, t_pway_human, t_dt_publication,
                                    t_dt_open, t_dt_close, t_url, tender['lots'])
            yield mapper

            self.logger.info('[tender-{}] PARSING OK'.format(t_url))

    def collect(self):
        while True:
            for mapper in self.tender_list_gen():
                # self.repository.upsert(mapper.tender_short_model)
                print(mapper)
                for model in mapper.tender_model_gen():
                    # self.rabbitmq.publish(model)
                    print(model)
