import datetime
import requests
import threading
import logging
import sys

from flask import abort, jsonify, request, Response, Blueprint
from flask_restful import reqparse, Resource, fields, marshal

from searcch_backend.models.model import (
    ImporterInstance )
from searcch_backend.models.schema import (
    ImporterInstanceSchema )
from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.auth import (
    verify_api_key, has_token, verify_token)
from searcch_backend.api.common.importer import schedule_import


LOG = logging.getLogger(__name__)

class ImporterCheckThread(threading.Thread):

    def __init__(self,importer_instance_id,is_new):
        super(ImporterCheckThread,self).__init__()
        self._importer_instance_id = importer_instance_id
        self.importer_instance = db.session.query(ImporterInstance)\
          .filter(ImporterInstance.id == importer_instance_id).first()
        self.is_new = is_new

    def run(self,*args,**kwargs):
        url = self.importer_instance.url + "/status"
        LOG.debug("checking importer %s (key %s)" %
            (url,self.importer_instance.key))
        old_status = self.importer_instance.status
        old_admin_status = self.importer_instance.admin_status
        try:
            r = requests.Session().get(url,headers={"X-Api-Key":self.importer_instance.key},
                             timeout=4)
            if r.status_code != requests.codes.ok:
                LOG.error("%s/status check failed (%d)" % (
                    self.importer_instance.url,r.status_code))
                self.importer_instance.status = "down"
                self.importer_instance.status_time = datetime.datetime.now()
                db.session.commit()
            else:
                LOG.debug("importer %s ok" % (url,))
                self.importer_instance.status = "up"
                self.importer_instance.status_time = datetime.datetime.now()
                if self.is_new:
                    self.importer_instance.admin_status = "enabled"
                    self.importer_instance.admin_status_time = datetime.datetime.now()
                db.session.add(self.importer_instance)
                db.session.commit()
        except:
            LOG.exception(sys.exc_info()[1])
            LOG.debug("importer %s not ok" % (url,))
            self.importer_instance.status = "down"
            self.importer_instance.status_time = datetime.datetime.now()
            db.session.commit()
            return

        # Invoke the scheduler in case we changed state.
        if self.importer_instance.status != old_status \
          or self.importer_instance.admin_status != old_admin_status:
            threading.Thread(target=schedule_import,name="schedule_import").start()

class ImporterResourceRoot(Resource):

    def __init__(self):
        super(ImporterResourceRoot, self).__init__()
        self.post_reqparse = reqparse.RequestParser()
        self.post_reqparse.add_argument(
            name="url", type=str, required=True,
            help="Importer instance URL required")
        self.post_reqparse.add_argument(
            name="key", type=str, required=True,
            help="The key with which to contact the importer instance.")
        self.post_reqparse.add_argument(
            name="max_tasks", type=int, required=True,
            help="The maximum number of parallel imports.")

    def post(self):
        """
        Importers register via this endpoint.
        """
        verify_api_key(request)
        
        args = self.post_reqparse.parse_args()
        if not args["url"] or not args["key"]:
            abort(400, description="must provide valid url and key")

        importer_instance = db.session.query(ImporterInstance)\
          .filter(ImporterInstance.url == args["url"])\
          .filter(ImporterInstance.key == args["key"]).first()
        if importer_instance:
            # In this case, we assume this is an importer instance that had to
            # restart, so we just allow it to think it was freshly created.
            LOG.info("importer instance %r re-registering" % (args["url"],))
            response = jsonify(ImporterInstanceSchema().dump(importer_instance))
            response.status_code = 200
            # Not a new importer, so don't allow it to move admin_status to
            # enabled; admin will have to do that.  Slight chance for a buggy
            # first registration to leave an importer in disabled state, but,
            # alas.
            ImporterCheckThread(importer_instance.id, False).start()
            return response
        importer_instance = db.session.query(ImporterInstance)\
          .filter(ImporterInstance.url == args["url"]).first()
        if importer_instance:
            abort(403, description="importer instance at url already exists")

        # Otherwise create a new one.
        dt = datetime.datetime.now()
        importer_instance = ImporterInstance(
            status="down",status_time=dt,admin_status="disabled",
            admin_status_time=dt,**args)

        db.session.add(importer_instance)
        db.session.commit()
        db.session.refresh(importer_instance)
        response = jsonify(ImporterInstanceSchema().dump(importer_instance))
        response.status_code = 200
        # This is a new registration, so give it a chance to move admin_status
        # to enabled.
        ImporterCheckThread(importer_instance.id, True).start()
        return response

    def get(self):
        """
        List all importer instances.
        """
        verify_api_key(request)
        login_session = None
        if has_token(request):
            login_session = verify_token(request)
        if login_session and not login_session.is_admin:
            abort(403, description="unauthorized")
        
        importer_instances = db.session.query(ImporterInstance).all()
        response = jsonify({"importers": ImporterInstanceSchema(many=True).dump(importer_instances)})
        response.status_code = 200
        return response


class ImporterResource(Resource):

    def get(self, importer_instance_id):
        """
        Get an importer instance's details.
        """
        verify_api_key(request)
        login_session = None
        if has_token(request):
            login_session = verify_token(request)
        if login_session and not login_session.is_admin:
            abort(403, description="unauthorized")
        
        importer_instance = db.session.query(ImporterInstance).filter(
            ImporterInstance.id == importer_instance_id).first()
        if not importer_instance:
            abort(404, description="invalid importer instance ID")

        response = jsonify({"importer": ImporterInstanceSchema().dump(importer_instance)})
        response.status_code = 200
        return response

    def put(self, importer_instance_id):
        """
        Allows the importer to push its status to us, or for admins to set admin_status.
        """
        verify_api_key(request)
        login_session = None
        if has_token(request):
            login_session = verify_token(request)

        if login_session and not login_session.is_admin:
            abort(401, description="unauthorized")

        importer_instance = db.session.query(ImporterInstance).filter(
            ImporterInstance.id == importer_instance_id).first()
        if not importer_instance:
            abort(404, description="invalid importer instance ID")

        j = request.json
        if "status" in j:
            if login_session:
                abort(401, description="only importer allowed to change status")
            if j["status"] not in ("up", "down"):
                abort(400, description="invalid status")
        if "admin_status" in j:
            if not login_session:
                abort(401, description="only admins allowed to change admin_status")
            if j["admin_status"] not in ("enabled", "disabled"):
                abort(400, description="invalid admin_status")

        status_changed = False
        if "status" in j:
            if importer_instance.status != j["status"]:
                status_changed = True
            importer_instance.status = j["status"]
            importer_instance.status_time = datetime.datetime.now()
        admin_status_changed = False
        if "admin_status" in j:
            if importer_instance.admin_status != j["admin_status"]:
                admin_status_changed = True
            importer_instance.admin_status = j["admin_status"]
            importer_instance.admin_status_time = datetime.datetime.now()
        db.session.commit()

        # Invoke the scheduler in case we changed state.
        if admin_status_changed or status_changed:
            threading.Thread(target=schedule_import,name="schedule_import").start()

        return Response(status=200)

    def delete(self, importer_instance_id):
        """
        Delete an importer instance.
        """
        # XXX: later on, need to validate this api key more tightly... only
        # admins and the instance itself should be allowed to delete, and then
        # only if not currently running.
        verify_api_key(request)
        login_session = None
        if has_token(request):
            login_session = verify_token(request)
        
        importer_instance = db.session.query(ImporterInstance).filter(
            ImporterInstance.id == importer_instance_id).first()
        if not importer_instance:
            abort(404, description="invalid importer instance ID")

        # To do this instantly, we have to reset the ArtifactImport's status
        # and deschedule.
        # XXX: need to handle this more nicely so that the importer actually
        # aborts instead of just getting odd errors when it updates an
        # existing job.
        if importer_instance.scheduled:
            for sched in importer_instance.scheduled:
                sched.artifact_import.status = "pending"
                sched.artifact_import.message = None
                sched.artifact_import.progress = 0.0
                sched.artifact_import.bytes_retrieved = 0
                sched.artifact_import.bytes_extracted = 0
                sched.artifact_import.log = None
                db.session.delete(sched)
                pass
            importer_instance.scheduled = []

        db.session.delete(importer_instance)
        db.session.commit()

        return Response(status=200)
