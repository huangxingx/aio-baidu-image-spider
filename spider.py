#!/usr/bin python
# -*- coding: utf-8 -*-

# @author: x.huang
# @date:10/07/18


import argparse
import asyncio
import hashlib
import logging
import os
import re
import shutil
import time
from urllib.parse import quote

import aiofiles
import aiohttp

logging.basicConfig(level=logging.INFO)

DEFAULT_IMAGE_DIR = '/var/image_data/aio_queue'
DEFAULT_COROUTINE_NUMBER = 30  # 协程数

parser = argparse.ArgumentParser()
parser.add_argument('keyword', type=str, help='search keyword like "model"')
parser.add_argument('-d', help='图片下载目录', type=str, dest='dir')
parser.add_argument('-n', help='协程数', type=int, dest='coroutine_number')
parser.add_argument('-w', '--width', type=int, help='the picture width')
parser.add_argument('-he', '--height', type=int, help='the picture height')
argv = parser.parse_args()

IMAGE_DIR = argv.dir or DEFAULT_IMAGE_DIR
COROUTINE_NUMBER = argv.coroutine_number or DEFAULT_COROUTINE_NUMBER
KEYWORD = argv.keyword
WIDTH = argv.width
HEIGHT = argv.height

event = asyncio.Event()

BD_DOWNLOAD_URL_PREFIX = 'https://image.baidu.com/search/down' \
                         '?tn=download&ipn=dwnl&word=download&ie=utf8&fr=result' \
                         '&url='


class BloomFilter:
    # 去重 URL
    url_dict = dict()

    @classmethod
    def is_contain(cls, item):
        if item in cls.url_dict:
            return True

        return False

    @classmethod
    def add(cls, item):
        cls.url_dict.setdefault(item, 0)


def check_image_dir_exist():
    """ 检查目录是否存在，存在则删除， 不存在则新建 """
    if os.path.exists(IMAGE_DIR):
        shutil.rmtree(IMAGE_DIR)

    os.mkdir(IMAGE_DIR)


async def download_url(q):
    """ 通过从队列获取url 下载到本地 """
    async with aiohttp.ClientSession() as session:
        while 1:
            try:
                url = q.get_nowait()

            except asyncio.QueueEmpty as e:
                await asyncio.sleep(1)
                if event.is_set():
                    if not q.empty():
                        logging.warning('untaskdone: %d' % q.qsize())
                    break
                continue

            try:
                async with session.get(url, timeout=10) as resp:
                    content = await resp.read()
                    if resp.status != 200:
                        logging.error(f'{resp.status}...{url}')
                        continue

                    # 判断是否获取到了正确的图片
                    if resp.content_length == 20:
                        # 获取的数据为空
                        end_index = len(BD_DOWNLOAD_URL_PREFIX)
                        org_url = url[end_index:]  # 原始 url
                        await put_in_queue(q, org_url)
                        continue

                    md5 = hashlib.md5(content).hexdigest()
                    file_path = os.path.join(IMAGE_DIR, md5 + '.jpg')
                    async with aiofiles.open(file_path, 'wb+') as f:
                        await f.write(content)
                        now = time.time()
                        logging.info(f'ok ... {file_path}... {now}...queue.size: {q.qsize()}')
                        q.task_done()

            except UnicodeDecodeError:
                logging.error(f'UnicodeDecodeError...{url}')

            except aiohttp.client_exceptions.ClientConnectorError:
                logging.error(f'ClientConnectorError...{url}')

            except asyncio.TimeoutError:
                logging.error(f'TimeoutError...{url}')


async def put_in_queue(q, download_image_url):
    if not BloomFilter.is_contain(download_image_url):
        BloomFilter.add(download_image_url)

        await q.put(download_image_url)


async def get_json_result(q):
    """ 解析url结果 获取 image_url put 到队列中 """

    key_word_o = KEYWORD
    width = WIDTH or 0
    height = HEIGHT or 0
    key_word = quote(key_word_o)

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36"
        }

    async with aiohttp.ClientSession(headers=headers) as session:
        # 百度搜索出来的图片做多能访问到接近2000张
        for num in range(0, 2000, 60):
            try:
                baidu_url = 'https://image.baidu.com/search/acjson?tn=resultjson_com&ipn=rj&ct=201326592&is=&fp=result&word={key_word}&ie=utf-8&width={width}&height={height}&pn={num}'
                # baidu_url = 'https://image.baidu.com/search/flip' \
                #             '?tn=baiduimage&ie=utf-8&word={key_word}&pn={num}&width={width}&height={height}'
                request_url = baidu_url.format(num=num, key_word=key_word, width=width, height=height)
                logging.info("request_url: %s", request_url)
                async with session.get(request_url, timeout=10) as resp:
                    content = await resp.read()
                    content = content.decode('utf-8')
                    reg = re.compile(r'"ObjURL":"(.*?)"')
                    # reg = re.compile(r'class="down".*href="(.*?)"')
                    image_data_list = re.findall(reg, content)
                    logging.info(image_data_list)
                    if not image_data_list:
                        continue
                    for image_url in image_data_list:
                        if image_url.startswith('http'):
                            image_url = image_url.replace("\/", "/")
                            image_url = quote(image_url)
                            download_image_url = BD_DOWNLOAD_URL_PREFIX + image_url
                
                            logging.info("download_image_url: %s", download_image_url)
                            await put_in_queue(q, download_image_url)

                logging.info(f'done...{request_url}')

            except UnicodeDecodeError:
                logging.error('UnicodeDecodeError')

            except aiohttp.client_exceptions.ClientConnectorError:
                logging.error('ClientConnectorError')


    # 结束信号
    event.set()


async def run(q, loop):
    """ 创建异步任务 """

    tasks = [loop.create_task(get_json_result(q))]

    tasks_download = [loop.create_task(download_url(q)) for _ in range(COROUTINE_NUMBER)]

    await asyncio.wait(tasks + tasks_download)


if __name__ == '__main__':
    check_image_dir_exist()

    queue = asyncio.Queue()
    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(run(queue, event_loop))
    event_loop.close()
