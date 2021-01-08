import datetime
import logging
import sys
import threading
import requests
import logging

from sqlalchemy import ( asc, desc, func )
from flask import abort, jsonify, request, Response, Blueprint
from flask_restful import reqparse, Resource, fields, marshal

from searcch_backend.models.model import (
    ARTIFACT_IMPORT_TYPES, ArtifactImport, ImporterSchedule,
    ImporterInstance )
from searcch_backend.models.schema import (
    ArtifactImportSchema )
from searcch_backend.api.app import db
from searcch_backend.api.common.auth import verify_api_key


LOG = logging.getLogger(__name__)

def notify_importer(artifact_import,importer_instance,importer_schedule,
                    session):
    """
    Posts an artifact_import to the given importer_instance.  If this
    fails for any reason, we immediately deschedule the import (unlink
    the artifact_import from the importer_schedule), and allow a
    future state mutation to reschedule it.
    """
    # XXX: do a better job tracking failure cause, e.g. connection error vs
    # http error status.  If the importer fails to accept our artifact_import,
    # something may be wrong with our POST request or the artifact_import
    # object.
    try:
        ais = ArtifactImportSchema(
            only=("id","type","url","importer_module_name","ctime"))
        aid = ais.dumps(artifact_import)
        LOG.debug("notifying importer %r of scheduled import %r (data=%r)" % (
            importer_instance, artifact_import,aid))
        r = requests.post(
            importer_instance.url + "/artifact/imports",
            headers={"Content-type":"application/json",
                     "X-Api-Key":importer_instance.key},
            data=aid)
        if r.status_code == requests.codes.ok:
            LOG.debug("notified importer %r of scheduled import %r" % (
                importer_instance, artifact_import))
            return
        else:
            LOG.error("failed to notify importer %r of scheduled import %r (status=%d); descheduling" % (
                importer_instance, artifact_import, r.status_code))
    except:
        LOG.error("failed to notify %r of scheduled import %r; descheduling" % (
            importer_instance,artifact_import))
        LOG.exception(sys.exc_info()[1])

    # If we arrive here, there was an error, so deschedule.
    importer_schedule.importer_instance_id = None
    importer_schedule.schedule_time = None
    artifact_import.status = "pending"
    artifact_import.mtime = datetime.datetime.now()
    session.flush()
    session.commit()

#
# We do not keep a scheduler thread running in the background.  Instead, this
# function is invoked every time an ArtifactImport or ImporterInstance changes
# state.
#
# NB: we also assume that all importer instances *do* keep a simple background
# thread that pushes state updates to us at regular, reasonable intervals (e.g.
# one minute).  We'll flip this around later so that the backend polls for
# status.
#
def schedule_import(*args,**kwargs):
    """
    Schedule an artifact_import to an importer_instance, if any
    importer_instance slots are available.  If the argument is None,
    look for the oldest unscheduled artifact_import.  This must be run
    in a separate thread.  Note that it creates its own scoped session
    and closes it before returning so that it doesn't leak sqlalchemy
    connections.
    """
    LOG.debug("schedule_import (thread=%r, threads=%r)" % (
        threading.current_thread().getName(),threading.active_count()))

    session = db.create_scoped_session()
    #session = db.session
    LOG.debug("session: %r" % (session,))
    #session.begin_nested()
    #session.begin()

    # Ensure there is at least one artifact_import to schedule:
    res = session.query(ImporterSchedule)\
      .filter(ImporterSchedule.importer_instance_id == None).all()
    if not res:
        LOG.debug("nothing to schedule")
        session.close()
        return

    # Unfortunately, we must lock to avoid races.
    #session.begin(subtransactions=True)
    #session.execute("BEGIN")
    #session.execute("LOCK TABLE ONLY importer_instances, importer_schedules")
    #session.execute("LOCK TABLE ONLY importer_schedules IN ACCESS EXCLUSIVE MODE")
    (artifact_import,importer_schedule,importer_instance) = (None,None,None)
    try:
        res = session.query(
            ImporterInstance.id.label("id"),
            ImporterInstance.max_tasks.label("max_tasks"),
            func.count(ImporterSchedule.id).label("current_tasks"))\
          .join(ImporterSchedule,
                ImporterInstance.id == ImporterSchedule.importer_instance_id,
                isouter=True)\
          .filter(ImporterInstance.status == "up")\
          .filter(ImporterInstance.admin_status == "enabled")\
          .group_by(ImporterInstance.id)\
          .order_by(desc(ImporterInstance.status_time)).all()
        if not res:
            LOG.warn("no up/enabled importers; cannot schedule")
            session.rollback()
            session.close()
            return

        (least_id,least_percent) = (None,100.0)
        for (id,max_tasks,current_tasks) in res:
            if current_tasks == max_tasks:
                continue
            pct = current_tasks/float(max_tasks)
            if pct < least_percent:
                least_percent = pct
                least_id = id
        if not least_id:
            LOG.warn("all importers are busy")
            session.rollback()
            session.close()
            return

        importer_instance = session.query(ImporterInstance)\
          .filter(ImporterInstance.id == least_id).one()
        LOG.debug("using importer %r" % (importer_instance,))

        (importer_schedule,artifact_import) = session.query(
            ImporterSchedule,ArtifactImport)\
          .join(ArtifactImport,ImporterSchedule.artifact_import_id == ArtifactImport.id)\
          .filter(ImporterSchedule.importer_instance_id == None)\
          .order_by(asc(ArtifactImport.ctime)).first()
        LOG.debug("scheduling %r" % (artifact_import,))

        dt = datetime.datetime.now()
        importer_schedule.importer_instance_id = importer_instance.id
        importer_schedule.schedule_time = dt
        artifact_import.status = "scheduled"
        artifact_import.mtime = dt
        session.commit()
    except:
        session.rollback()
        session.close()
        LOG.error("error in schedule_import:")
        LOG.exception(sys.exc_info()[1])
        return

    # Notify the importer instance now that we've scheduled and released locks:
    notify_importer(artifact_import,importer_instance,importer_schedule,session)

    session.close()
