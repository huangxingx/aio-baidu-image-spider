#!/usr/bin/env python
# -*- coding: utf-8 -*-

# @author: x.huang
# @date:10/07/18


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

IMAGE_DIR = '/var/image_data/aio_queue'
logging.basicConfig(level=logging.INFO)

event = asyncio.Event()


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
                    break
                continue

            async with session.get(url) as resp:
                content = await resp.read()
                md5 = hashlib.md5(content).hexdigest()
                file_path = os.path.join(IMAGE_DIR, md5 + '.jpg')
                async with aiofiles.open(file_path, 'wb+') as f:
                    await f.write(content)
                    now = time.time()
                    logging.info(f'ok ... {file_path}... {now}')
                    q.task_done()


async def get_json_result(q, key_word):
    """ 解析url结果 获取 image_url put 到队列中 """
    async with aiohttp.ClientSession() as session:

        # 百度搜索出来的图片做多能访问到接近2000张
        for num in range(0, 2000, 20):
            try:
                baidu_url = 'https://image.baidu.com/search/flip?tn=baiduimage&ie=utf-8&word={key_word}&pn={num}'
                request_url = baidu_url.format(num=num, key_word=key_word)
                async with session.get(request_url) as resp:
                    content = await resp.read()
                    content = content.decode('utf-8')
                    reg = re.compile(r'"middleURL":"(.*?)"')
                    image_data_list = re.findall(reg, content)

                    for image_url in image_data_list:
                        if image_url.endswith('jpg'):
                            await q.put(image_url)

                logging.info(f'done...{request_url}')

            except UnicodeDecodeError:
                logging.error('UnicodeDecodeError')

            except aiohttp.client_exceptions.ClientConnectorError:
                logging.error('ClientConnectorError')
    event.set()


async def run(q, loop):
    """ 创建异步任务 """

    key_word_o = '模特'

    key_word = quote(key_word_o)
    tasks = [loop.create_task(get_json_result(q, key_word))]

    tasks_download = [loop.create_task(download_url(q)) for _ in range(5)]

    await asyncio.wait(tasks + tasks_download)


if __name__ == '__main__':
    check_image_dir_exist()

    queue = asyncio.Queue()
    event_loop = asyncio.get_event_loop()
    event_loop.run_until_complete(run(queue, event_loop))
