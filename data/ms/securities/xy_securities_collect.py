#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# author yanpan
# 2022/06/30 13:19
# 兴业证券

import os
import sys
import traceback
from configparser import ConfigParser

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(BASE_DIR)
from data.ms.basehandler import BaseHandler
from utils.deal_date import ComplexEncoder

from utils.exceptions_utils import ProxyTimeOutEx
import os
import json
import time
import xlrd2
from utils.logs_utils import logger
import datetime

target_excel_name = '兴业证券融资融券标的证券及保证金比例明细表'
guaranty_excel_name = '兴业证券融资融券可充抵保证金证券及折算率明细表'

guaranty_file_path = './' + 'guaranty.xlsx'
target_file_path = './' + 'target.xlsx'

base_dir = os.path.dirname(os.path.abspath(__file__))
full_path = os.path.join(base_dir, '../../../config/config.ini')
cf = ConfigParser()
cf.read(full_path, encoding='utf-8')
paths = cf.get('excel-path', 'save_excel_file_path')
save_excel_file_path_bd = os.path.join(paths, "兴业证券标的券{}.xlsx".format(datetime.date.today()))
save_excel_file_path_bzj = os.path.join(paths, "兴业证券保证金券{}.xlsx".format(datetime.date.today()))

exchange_mt_guaranty_security = '2'  # 融资融券可充抵保证金证券
exchange_mt_underlying_security = '3'  # 融资融券标的证券
exchange_mt_financing_underlying_security = '4'  # 融资融券融资标的证券
exchange_mt_lending_underlying_security = '5'  # 融资融券融券标的证券
exchange_mt_guaranty_and_underlying_security = '99'  # 融资融券可充抵保证金证券和融资融券标的证券

data_source = '兴业证券'
_url = "https://static.xyzq.cn/xywebsite/attachment/3B8333A8CD0845A9A2.xlsx"
url_ = "https://static.xyzq.cn/xywebsite/attachment/B21E17122E41411497.xlsx"


class CollectHandler(BaseHandler):

    @classmethod
    def collect_data(cls, business_type):
        max_retry = 0
        while max_retry < 3:
            logger.info(f'重试第{max_retry}次')
            if business_type:
                if business_type == 3:
                    try:
                        # 兴业证券标的相关数据采集
                        cls.target_collect_task()
                        break
                    except ProxyTimeOutEx as es:
                        pass
                    except Exception as e:
                        logger.error(f'{data_source}标的证券采集任务异常，请求url为：{_url}，具体异常信息为：{traceback.format_exc()}')
                elif business_type == 2:
                    try:
                        # 兴业证券保证金相关数据采集
                        cls.guaranty_collect_task()
                        break
                    except ProxyTimeOutEx as es:
                        pass
                    except Exception as e:
                        logger.error(f'{data_source}保证金证券采集任务异常，请求url为：{url_}，具体异常信息为：{traceback.format_exc()}')

            max_retry += 1

    # 兴业证券标的相关数据采集
    @classmethod
    def target_collect_task(cls):
        actual_date = datetime.date.today()
        logger.info(f'开始采集兴业证券融资融券融资标的相关数据{actual_date}')
        excel_one_download_url = "https://static.xyzq.cn/xywebsite/attachment/3B8333A8CD0845A9A2.xlsx"

        try:
            data = None
            proxies = super().get_proxies()
            response = super().get_response(data_source, excel_one_download_url, proxies, 0)
            if response is None or response.status_code != 200:
                raise Exception(
                    f'{data_source}数据采集任务请求响应获取异常,已获取代理ip为:{proxies}，请求url为:{excel_one_download_url},请求参数为:{data}')
            if response.status_code == 200:
                with open(target_file_path, 'wb') as file:
                    file.write(response.content)
                with open(save_excel_file_path_bd, 'wb') as file:
                    file.write(response.content)
                    excel_file = xlrd2.open_workbook(target_file_path)
                    cls.target_collect(excel_file, excel_one_download_url)
        except ProxyTimeOutEx as e:
            pass
        except Exception as es:
            raise Exception(es)
        finally:
            remove_file(target_file_path)

    @classmethod
    def target_collect(cls, excel_file, excel_one_download_url):
        actual_date = datetime.date.today()
        start_dt = datetime.datetime.now()
        try:
            sheet_0 = excel_file.sheet_by_index(0)
            total_row = sheet_0.nrows
            data_list = []
            data_tile = ['no', 'sec_code', 'sec_name', 'rz_rate', 'rq_rate']
            for i in range(1, total_row):
                row = sheet_0.row(i)
                if row is None:
                    break
                no = str(row[0].value)
                sec_code = str(row[1].value)
                sec_name = str(row[2].value)
                rz_rate = str(row[4].value)
                rq_rate = str(row[5].value)

                data_list.append((no, sec_code, sec_name, rz_rate, rq_rate))

            logger.info(f'采集兴业证券融资融券融资标的相关数据结束，共{int(len(data_list))}条')
            df_result = super().data_deal(data_list, data_tile)
            end_dt = datetime.datetime.now()
            used_time = (end_dt - start_dt).seconds
            if df_result is not None:
                data_status = 1
                super().data_insert(int(len(data_list)), df_result, actual_date,
                                    exchange_mt_underlying_security,
                                    data_source, start_dt, end_dt, used_time, excel_one_download_url, data_status)
                logger.info(f'入库信息,共{int(len(data_list))}条')

            message = "xy_securities_collect"
            super().kafka_mq_producer(json.dumps(actual_date, cls=ComplexEncoder),
                                      exchange_mt_underlying_security, data_source, message)

            logger.info("兴业证券融资融券标的证券数据采集完成")
        except Exception as e:
            data_status = 2
            super().data_insert(0, str(e), actual_date, exchange_mt_underlying_security,
                                data_source, start_dt, None, None, excel_one_download_url, data_status)

            raise Exception(e)

    # 兴业证券融资融券可充抵保证金证券及折算率数据采集
    @classmethod
    def guaranty_collect_task(cls):
        actual_date = datetime.date.today()
        logger.info(f'开始采集兴业证券保证金证券相关数据{actual_date}')
        excel_two_download_url = "https://static.xyzq.cn/xywebsite/attachment/B21E17122E41411497.xlsx"

        try:
            data = None
            proxies = super().get_proxies()
            response = super().get_response(data_source, excel_two_download_url, proxies, 0)
            if response is None or response.status_code != 200:
                raise Exception(
                    f'{data_source}数据采集任务请求响应获取异常,已获取代理ip为:{proxies}，请求url为:{excel_two_download_url},请求参数为:{data}')
            if response.status_code == 200:
                with open(guaranty_file_path, 'wb') as file:
                    file.write(response.content)
                with open(save_excel_file_path_bzj, 'wb') as file:
                    file.write(response.content)
                    excel_file = xlrd2.open_workbook(guaranty_file_path)
                    cls.guaranty_collect(excel_file, excel_two_download_url)
        except ProxyTimeOutEx as e:
            pass
        except Exception as es:
            raise Exception(es)
        finally:
            remove_file(guaranty_file_path)

    @classmethod
    def guaranty_collect(cls, excel_file, excel_two_download_url):
        actual_date = datetime.date.today()
        start_dt = datetime.datetime.now()
        try:
            sheet_0 = excel_file.sheet_by_index(0)
            total_row = sheet_0.nrows
            data_list = []
            data_tile = ['no', 'sec_code', 'sec_name', 'discount_rate']
            current_read_part = 1  # 担保券excel文件的sheet0分两部份，要遍历2次
            total_part = 2
            reading_row_num = 1  # 从第2行开始遍历
            reading_column_num = 0  # 从第几列开始读,第一部份是第0列,第二部分是第5列,用于判断该部份是否有数据，没有数据就认为结束
            while reading_row_num < total_row and current_read_part <= total_part:
                row = sheet_0.row(reading_row_num)
                if row[reading_column_num].value == '':
                    reading_row_num = 1  # 读到空行结束当前部份，重置行号
                    current_read_part = current_read_part + 1  # 下一部份
                    reading_column_num = reading_column_num + 5
                    continue

                reading_row_num = reading_row_num + 1  # 行号+1

                if current_read_part == 1:  # 读第1部份数据(左侧)
                    no = str(row[0].value)
                    sec_code = str(row[1].value)
                    sec_name = str(row[2].value)
                    discount_rate = str(row[3].value)
                else:  # 读第2部份数据(右侧)
                    no = str(row[5].value)
                    sec_code = str(row[6].value)
                    sec_name = str(row[7].value)
                    discount_rate = str(row[8].value)

                data_list.append((no, sec_code, sec_name, discount_rate))

            logger.info(f'采集兴业证券保证金数据结束，共{int(len(data_list))}条')
            df_result = super().data_deal(data_list, data_tile)
            end_dt = datetime.datetime.now()
            used_time = (end_dt - start_dt).seconds
            if df_result is not None:
                data_status = 1
                super().data_insert(int(len(data_list)), df_result, actual_date,
                                    exchange_mt_guaranty_security,
                                    data_source, start_dt, end_dt, used_time, excel_two_download_url, data_status)
                logger.info(f'入库信息,共{int(len(data_list))}条')

            message = "xy_securities_collect"
            super().kafka_mq_producer(json.dumps(actual_date, cls=ComplexEncoder),
                                      exchange_mt_guaranty_security, data_source, message)

            logger.info("兴业证券保证金证券数据采集完成")
        except Exception as e:
            data_status = 2
            super().data_insert(0, str(e), actual_date, exchange_mt_guaranty_security,
                                data_source, start_dt, None, None, excel_two_download_url, data_status)

            raise Exception(e)


def remove_file(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        raise Exception(e)


if __name__ == '__main__':
    collector = CollectHandler()
    # collector.collect_data(3)
    collector.collect_data(eval(sys.argv[1]))
