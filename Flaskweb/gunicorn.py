import gevent.monkey

gevent.monkey.patch_all()

import multiprocessing
import os

filePath = "gunicornLog"
if not os.path.exists(filePath):
    os.mkdir(filePath)

debug = True
logLevel = 'debug'
bind = '0.0.0.0:5080'
pidFile = filePath + '/gunicorn.pid'
logFile = filePath + '/debug.log'
errorLog = filePath + '/error.log'
accessLog = filePath + '/access.log'

# 启动的进程数
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'gunicorn.workers.ggevent.GeventWorker'

x_forwarded_for_header = 'X-FORWARDED-FOR'