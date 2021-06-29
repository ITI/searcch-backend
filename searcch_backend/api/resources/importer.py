import datetime
import requests
import threading
import logging

from flask import abort, jsonify, request, Response, Blueprint
from flask_restful import reqparse, Resource, fields, marshal

from searcch_backend.models.model import (
    ImporterInstance )
from searcch_backend.models.schema import (
    ImporterInstanceSchema )
from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.auth import verify_api_key
from searcch_backend.api.common.importer import schedule_import


LOG = logging.getLogger(__name__)

class ImporterCheckThread(threading.Thread):

    def __init__(self,importer_instance_id):
        super(ImporterCheckThread,self).__init__()
        self._importer_instance_id = importer_instance_id
        self.importer_instance = db.session.query(ImporterInstance)\
          .filter(ImporterInstance.id == importer_instance_id).first()

    def run(self,*args,**kwargs):
        r = requests.get(self.importer_instance.url + "/status",
                         headers={"X-Api-Key":self.importer_instance.key})
        if r.status_code != requests.codes.ok:
            LOG.error("%s/status check failed (%d)" % (
                self.importer_instance.url,r.status_code))
            return
        self.importer_instance.admin_status = "enabled"
        self.importer_instance.admin_status_time = datetime.datetime.now()
        db.session.add(self.importer_instance)
        db.session.commit()
        LOG.debug("%r ok" % (self.importer_instance),)
        # Invoke the scheduler in case we changed state.
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
            ImporterCheckThread(importer_instance.id).start()
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
        ImporterCheckThread(importer_instance.id).start()
        return response

    def get(self):
        """
        List all importer instances.
        """
        verify_api_key(request)
        
        importer_instances = db.session.query(ImporterInstance).all()
        response = jsonify({"importers": importer_instances})
        response.status_code = 200
        return response


class ImporterResource(Resource):

    def get(self, importer_instance_id):
        """
        Get an importer instance's details.
        """
        verify_api_key(request)
        
        importer_instance = db.session.query(ImporterInstance).filter(
            ImporterInstance.id == importer_instance_id).first()
        if not importer_instance:
            abort(404, description="invalid importer instance ID")

        response = jsonify(importer_instance)
        response.status_code = 200
        return response

    def put(self, importer_instance_id):
        """
        Allows the importer to push its status to us.
        """
        verify_api_key(request)
        
        importer_instance = db.session.query(ImporterInstance).filter(
            ImporterInstance.id == importer_instance_id).first()
        if not importer_instance:
            abort(404, description="invalid importer instance ID")

        j = request.json
        if not "status" in j or j["status"] not in ("up","down"):
            abort(401, description="invalid status")

        importer_instance.status = j["status"]
        importer_instance.status_time = datetime.datetime.now()
        db.session.add(importer_instance)
        db.session.commit()

        LOG.debug("about to schedule_import (thread=%r, threads=%r)" % (
            threading.current_thread().getName(),threading.active_count()))

        # Invoke the scheduler in case we changed state.
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
        
        importer_instance = db.session.query(ImporterInstance).filter(
            ImporterInstance.id == importer_instance_id).first()
        if not importer_instance:
            abort(404, description="invalid importer instance ID")

        

        db.session.delete(importer_instance)
        db.session.commit()

        return Response(status=200)
