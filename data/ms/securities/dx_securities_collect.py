#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# author yanpan
# 2022/07/01 15:19
# 东兴证券

import os
import sys
import traceback

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(BASE_DIR)

from utils.exceptions_utils import ProxyTimeOutEx
from data.ms.basehandler import BaseHandler
from utils.deal_date import ComplexEncoder

import datetime
import json
from utils.logs_utils import logger
from selenium.webdriver.common.by import By
import time
from bs4 import BeautifulSoup

exchange_mt_guaranty_security = '2'  # 融资融券可充抵保证金证券
exchange_mt_underlying_security = '3'  # 融资融券标的证券
exchange_mt_financing_underlying_security = '4'  # 融资融券融资标的证券
exchange_mt_lending_underlying_security = '5'  # 融资融券融券标的证券
exchange_mt_guaranty_and_underlying_security = '99'  # 融资融券可充抵保证金证券和融资融券标的证券

data_source = '东兴证券'
url_ = 'https://www.dxzq.net/main/rzrq/gsxx/rzrqdq/index.shtml?catalogId=1,10,60,144'
_url = 'https://www.dxzq.net/main/rzrq/gsxx/kcdbzjzq/index.shtml?catalogId=1,10,60,145'


class CollectHandler(BaseHandler):

    @classmethod
    def collect_data(cls, business_type):
        max_retry = 0
        while max_retry < 3:
            logger.info(f'重试第{max_retry}次')
            if business_type:
                if business_type == 3:
                    try:
                        # 东兴证券融资融券标的证券采集
                        cls.rzrq_target_collect()
                        break
                    except ProxyTimeOutEx as es:
                        pass
                    except Exception as e:
                        logger.error(f'{data_source}融资融券标的证券采集任务异常，请求url为：{url_}，具体异常信息为：{traceback.format_exc()}')
                elif business_type == 2:
                    try:
                        # 东兴证券可充抵保证金证券采集
                        cls.guaranty_collect()
                        break
                    except ProxyTimeOutEx as es:
                        pass
                    except Exception as e:
                        logger.error(f'{data_source}可充抵保证金证券采集任务异常，请求url为：{_url}，具体异常信息为：{traceback.format_exc()}')

            max_retry += 1

    @classmethod
    def rzrq_target_collect(cls):
        actual_date = datetime.date.today()
        logger.info(f'开始采集东兴证券融资融券标的证券数据{actual_date}')
        # 融资融券标的证券
        url = 'https://www.dxzq.net/main/rzrq/gsxx/rzrqdq/index.shtml?catalogId=1,10,60,144'
        start_dt = datetime.datetime.now()

        try:
            driver = super().get_driver()
            driver.get(url)
            original_data_list = []

            # 找到总页数
            total_page = 0
            li_elements = driver.find_elements(By.XPATH, "//span[contains(@class, 'all')]/em")
            if len(li_elements) > 0:
                total_page = li_elements[len(li_elements) - 1].text

            # 当前网页内容(第1页)
            html_content = str(driver.page_source)
            logger.info("东兴标的券第{}页,共10条".format(1))
            cls.resolve_single_target_page(html_content, original_data_list)
            target_title = ['date', 'stock_code', 'stock_name', 'rz_rate', 'rq_rate']

            # 找到下一页 >按钮
            # elements = driver.find_elements(By.XPATH, "//button[@class='ant-pagination-item-link']")
            # next_page_button_element = elements[1]
            for_count = int(total_page) + 1
            for current_page in range(2, for_count):
                driver.implicitly_wait(120)
                driver.execute_script("toPage({current_page})".format(current_page=current_page))
                time.sleep(1)

                # 处理第[2, total_page]页html
                html_content = str(driver.page_source)
                logger.info("东兴标的券第{}页，共10条".format(current_page))
                cls.resolve_single_target_page(html_content, original_data_list)

            logger.info("采集东兴证券融资融券标的证券数据结束")
            df_result = super().data_deal(original_data_list, target_title)
            end_dt = datetime.datetime.now()
            used_time = (end_dt - start_dt).seconds
            if df_result is not None:
                data_status = 1
                super().data_insert(int(len(original_data_list)), df_result, actual_date,
                                    exchange_mt_underlying_security,
                                    data_source, start_dt, end_dt, used_time, url, data_status)
                logger.info(f'入库信息,共{int(len(original_data_list))}条')

            message = "dx_securities_collect"
            super().kafka_mq_producer(json.dumps(actual_date, cls=ComplexEncoder),
                                      exchange_mt_underlying_security, data_source, message)

            logger.info("东兴证券融资融券标的证券数据采集完成")
        except Exception as e:
            data_status = 2
            super().data_insert(0, str(e), actual_date, exchange_mt_underlying_security,
                                data_source, start_dt, None, None, url, data_status)

            raise Exception(e)

    @classmethod
    def resolve_single_target_page(cls, html_content, original_data_list):
        soup = BeautifulSoup(html_content, "html.parser")
        # label_td_div_list = soup.select('tbody tr')
        label_td_div_list = soup.select('td:nth-child(-n+5)')
        # del label_td_div_list[0]
        row_id = 0
        for i in label_td_div_list:
            if row_id % 5 == 0:
                row_list = []
                original_data_list.append(row_list)
            row_id += 1

            text = i.text
            if '\n' in text:
                text = str(text).replace("\n", ",").strip()
                text = text[1:len(text) - 2]
            row_list.append(text)

    @classmethod
    def guaranty_collect(cls):
        actual_date = datetime.date.today()
        logger.info(f'开始采集东兴证券可充抵保证金证券数据{actual_date}')
        start_dt = datetime.datetime.now()
        # 可充抵保证金证券
        url = 'https://www.dxzq.net/main/rzrq/gsxx/kcdbzjzq/index.shtml?catalogId=1,10,60,145'

        try:
            driver = super().get_driver()
            driver.get(url)
            original_data_list = []

            # 找到总页数
            total_page = 0
            li_elements = driver.find_elements(By.XPATH, "//span[contains(@class, 'all')]/em")
            if len(li_elements) > 0:
                total_page = li_elements[len(li_elements) - 1].text

            # 当前网页内容(第1页)
            html_content = str(driver.page_source)
            logger.info("东兴可充抵保证金券第{}页，共10条".format(1))
            cls.resolve_single_target_page_ohter(html_content, original_data_list)
            target_title = ['date', 'stock_code', 'stock_name', 'discount_rate']
            # 找到下一页 >按钮
            for_count = int(total_page.replace(',', '')) + 1
            for current_page in range(2, for_count):
                driver.implicitly_wait(120)
                driver.execute_script("toPage({current_page})".format(current_page=current_page))
                time.sleep(0.5)

                # 处理第[2, total_page]页html
                html_content = str(driver.page_source)
                logger.info("东兴可充抵保证金券第{}页，共10条".format(current_page))
                cls.resolve_single_target_page_ohter(html_content, original_data_list)

            logger.info("采集东兴证券可充抵保证金担保券数据结束")
            df_result = super().data_deal(original_data_list, target_title)
            end_dt = datetime.datetime.now()
            used_time = (end_dt - start_dt).seconds
            if df_result is not None:
                data_status = 1
                super().data_insert(int(len(original_data_list)), df_result, actual_date,
                                    exchange_mt_guaranty_security,
                                    data_source, start_dt, end_dt, used_time, url, data_status)
                logger.info(f'入库信息,共{int(len(original_data_list))}条')

            message = "dx_securities_collect"
            super().kafka_mq_producer(json.dumps(actual_date, cls=ComplexEncoder),
                                      exchange_mt_guaranty_security, data_source, message)

            logger.info("东兴证券可充抵保证金担保券数据采集完成")
        except Exception as e:
            data_status = 2
            super().data_insert(0, str(e), actual_date, exchange_mt_guaranty_security,
                                data_source, start_dt, None, None, url, data_status)

            raise Exception(e)

    @classmethod
    def resolve_single_target_page_ohter(cls, html_content, original_data_list):
        soup = BeautifulSoup(html_content, "html.parser")
        label_td_div_list = soup.select('td:nth-child(-n+4)')
        row_id = 0
        for i in label_td_div_list:
            if row_id % 4 == 0:
                row_list = []
                original_data_list.append(row_list)
            row_id += 1

            text = i.text
            if '\n' in text:
                text = str(text).replace("\n", ",").strip()
                text = text[1:len(text) - 2]
            row_list.append(text)


if __name__ == '__main__':
    collector = CollectHandler()
    # collector.collect_data(3)
    collector.collect_data(eval(sys.argv[1]))
