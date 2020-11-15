import multiprocessing

bind = "128.9.160.71:80"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gevent"
threads = 2 * multiprocessing.cpu_count()
timeout = 600
accesslog = "logs/access.log"
errorlog = "logs/error.log"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
loglevel = "debug"
pidfile = "logs/process_id.pid"
capture_output = True
enable_stdio_inheritance = True
daemon = True