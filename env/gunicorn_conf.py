import multiprocessing

bind = "0.0.0.0:80"
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
daemon = True

#
# NB: something in our import chain imports requests before the gevent worker
# monkey patches requests.  So make sure it's done immediately.
#
if worker_class == "gevent":
    import gevent
    import gevent.monkey
    gevent.monkey.patch_all()

#
# NB: early exceptions from the app may be lost when workers fail immediately.
# Set preload_app = True if workers fail with no apparent cause; then you'll
# see exceptions.
#

#preload_app = True

def on_starting(server):
    from searcch_backend.api.app import (app, config, db, mail, migrate)
    from searcch_backend.api.common.alembic import maybe_auto_upgrade_db
    from searcch_backend.api.common.scheduled_tasks import SearcchBackgroundTasks

    # Run DB migrations
    maybe_auto_upgrade_db(app, db, migrate)

    #Run Scheduler
    SearcchBackgroundTasks(config, db, mail)
