import sys
import logging

from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
import tornado.autoreload
import tornado.options


from app import app  # 这里导入的是flsk项目的运行模块
import cron

settings = {'debug': True}


class LogFormatter(tornado.log.LogFormatter):
    def __init__(self):
        super(LogFormatter, self).__init__(
            fmt='%(color)s[%(asctime)s %(filename)s:%(funcName)s:%(lineno)d %(levelname)s]%(end_color)s %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )


# # tornado.options.define("log_file_prefix", default="./log/app.log")

tornado.options.parse_command_line()
[i.setFormatter(LogFormatter()) for i in logging.getLogger().handlers]
port = 9000
http_server = HTTPServer(WSGIContainer(app))
http_server.listen(port)
num = 1

if sys.platform == 'linux':
    num = 2

http_server.start(num)

cron.start()
IOLoop.instance().start()
