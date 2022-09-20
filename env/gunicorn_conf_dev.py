import multiprocessing

bind = "0.0.0.0:8080"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gevent"
threads = 2 * multiprocessing.cpu_count()
timeout = 600
accesslog = "logs/access.log"
errorlog = "logs/error.log"
access_log_format = '%({X-Real-IP}i)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
loglevel = "debug"
pidfile = "logs/process_id.pid"
capture_output = True
enable_stdio_inheritance = True
daemon = False

#
# NB: early exceptions from the app may be lost when workers fail immediately.
# Set preload_app = True if workers fail with no apparent cause; then you'll
# see exceptions.
#
#preload_app = True
