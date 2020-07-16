import sys

from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
import tornado.autoreload
import tornado.options


from app import app  # 这里导入的是flsk项目的运行模块
import cron

settings = {'debug': True}

tornado.options.parse_command_line()

port = 9000
http_server = HTTPServer(WSGIContainer(app))
http_server.listen(port)
http_server.start(2)

cron.start()
IOLoop.instance().start()
