## aio-baidu-image-spider
异步爬虫-爬取百度图片

#### spider

```shell
(aio-baidu-image-spider) ➜  aio-baidu-image-spider (master) ✗ python3 spider.py -h                            
usage: spider.py [-h] [-d DIR] [-n COROUTINE_NUMBER] [-w WIDTH] [-he HEIGHT] keyword

positional arguments:
  keyword               search keyword like "model"

optional arguments:
  -h, --help            show this help message and exit
  -d DIR                图片下载目录
  -n COROUTINE_NUMBER   协程数
  -w WIDTH, --width WIDTH
                        the picture width
  -he HEIGHT, --height HEIGHT
                        the picture height
```

example： 
```shell
python3 spider.py -d ./download  美女
```