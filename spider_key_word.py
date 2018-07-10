#!/usr/bin/env python
# -*- coding: utf-8 -*-

# @author: x.huang
# @date:05/07/18
import re

import requests


def get_json_result(url):
    resp = requests.get(url)
    key_word_list = []
    if resp.status_code == 200:
        content = resp.content
        reg = re.compile(r'name: "(.*?)"')
        key_word_list = re.findall(reg, content.decode('utf-8'))
    return key_word_list


def write_to_file(key_word_list):
    with open('key_word.txt', 'w+') as f:
        for line in key_word_list:
            if len(line.split()) > 2:
                f.write(line + '\n')


def main():
    baidu_url = 'https://image.baidu.com/search/index?tn=baiduimage&ie=utf-8&word=%E5%A3%81%E7%BA%B8&ct=201326592&ic=0&lm=-1&width=&height=&v=index'
    key_word_list = get_json_result(baidu_url)
    write_to_file(key_word_list)


if __name__ == '__main__':
    main()
