import datetime
import dateutil.parser
import logging
import sys
import threading
import traceback

import sqlalchemy
from sqlalchemy import asc, desc, sql, not_
from flask import abort, jsonify, request, Response, Blueprint
from flask_restful import reqparse, Resource, fields, marshal

from searcch_backend.models.model import (
    ArtifactImport, ImporterSchedule, ImporterInstance,
    Artifact, User,
    ARTIFACT_IMPORT_TYPES,
    ARTIFACT_IMPORT_STATUSES, ARTIFACT_IMPORT_PHASES )
from searcch_backend.models.schema import (
    ArtifactImportSchema )
from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.auth import verify_api_key
from searcch_backend.api.common.importer import schedule_import
from searcch_backend.api.common.sql import object_from_json

LOG = logging.getLogger(__name__)

class ArtifactImportResourceRoot(Resource):

    def __init__(self):
        self.postparse = reqparse.RequestParser()
        self.postparse.add_argument(
            name="userid", type=int, required=True, nullable=False,
            help="userid argument required")
        self.postparse.add_argument(
            name="url", type=str, required=True, nullable=False,
            help="Artifact source URL required")
        self.postparse.add_argument(
            name="importer_module_name", type=str, required=False,
            help="A specific importer name to use")
        self.postparse.add_argument(
            name="type", type=str, required=False,
            help="A specific type of artifact; defaults to `unknown`; one of (%s)" % (
                ",".join(ARTIFACT_IMPORT_TYPES)))

        self.getparse = reqparse.RequestParser()
        self.getparse.add_argument(
            name="userid", type=int, required=True, location="args", nullable=False,
            help="userid argument required")
        self.getparse.add_argument(
            name="status", type=str, required=False, location="args",
            help="status must be one of pending,scheduled,running,completed,failed")
        self.getparse.add_argument(
            name="archived", type=bool, required=False, location="args",
            default=False, help="if set True, show archived imports")

        super(ArtifactImportResourceRoot, self).__init__()

    def get(self):
        """
        Get a list of artifact imports.  May be filtered by userid
        (currently required) or status (optional)
        (pending,scheduled,running,completed,failed).
        """
        api_key = request.headers.get('X-Api-Key')
        verify_api_key(api_key, config_name)

        args = self.getparse.parse_args()
        userid = args["userid"]
        status = args["status"]

        user = db.session.query(User).filter(User.id == userid).first()
        if not user:
            abort(404, description="no such user")

        artifact_imports = db.session.query(ArtifactImport)\
          .filter(ArtifactImport.owner_id == userid)\
          .order_by(desc(ArtifactImport.id))
        if status:
            artifact_imports = artifact_imports.filter(ArtifactImport.status == status)
        if not args["archived"]:
            artifact_imports = artifact_imports.filter(ArtifactImport.archived == False)
        #else:
        #    artifact_imports = db.session.query(ArtifactImport)\
        #      .filter(ArtifactImport.owner_id == userid).all()
        artifact_imports = artifact_imports.all()

        response = jsonify({"artifact_imports": ArtifactImportSchema(many=True).dump(artifact_imports)})
        response.status_code = 200
        return response


    def post(self):
        """
        This is the primary artifact creation method.  It takes as input a URL, the uid, and possibly a specific importer to use.  It creates a temporary import session once handed off to the importer, and the frontend then polls based off the import session for completion of the import.  This is asynchronous, and returns an import session ID, if sanity checks succeed (e.g., an importer of the given name (if any) exists, rate limits are within tolerances, etc).  Note that the initial checks do *not* include URL reachability, since URLs may not all be reachable nor veriable over a basic HTTP(S) connection; the importer module must handle this case.  Finally, we cannot wait for the importer to do this reachability check, because there might be a queue of imports already being processed.
        """
        api_key = request.headers.get('X-Api-Key')
        verify_api_key(api_key, config_name)

        args = self.postparse.parse_args()
        if not args["url"]:
            abort(400, description="must provide non-null URL")
        if args["type"] and args["type"] not in ARTIFACT_IMPORT_TYPES:
            abort(400, description="invalid artifact type")
        userid = args["userid"]
        del args["userid"]

        res = db.session.query(ArtifactImport).\
          filter(ArtifactImport.url == args["url"]).\
          filter(ArtifactImport.owner_id == userid).\
          filter(ArtifactImport.artifact_id == None).\
          filter(not_(ArtifactImport.status.in_(["completed","failed"]))).\
          all()
        if len(res) > 0:
            abort(400, description="userid %r already importing from %r" % (userid,args["url"]))

        dt = datetime.datetime.now()
        ai = ArtifactImport(
            **args,owner_id=userid,ctime=dt,mtime=dt,status="pending",
            phase="start",archived=False)
        ims = ImporterSchedule(artifact_import=ai)
        db.session.add(ai)
        db.session.add(ims)
        db.session.commit()
        db.session.refresh(ai)

        LOG.debug("scheduling %r" % (ai,))
        threading.Thread(target=schedule_import,name="schedule_import").start()

        response = jsonify(ArtifactImportSchema().dump(ai))
        response.status_code = 200

        return response


class ArtifactImportResource(Resource):

    def __init__(self):
        self.putparse = reqparse.RequestParser()
        self.putparse.add_argument(
            name="userid", type=int, required=False)
        self.putparse.add_argument(
            name="mtime", type=str, required=False,
            help="mtime argument required (ISO-formatted timestamp)")
        self.putparse.add_argument(
            name="status", type=str, required=False)
        self.putparse.add_argument(
            name="phase", type=str, required=False)
        self.putparse.add_argument(
            name="message", type=str, required=False)
        self.putparse.add_argument(
            name="progress", type=float, required=False)
        self.putparse.add_argument(
            name="bytes_retrieved", type=int, required=False)
        self.putparse.add_argument(
            name="bytes_extracted", type=int, required=False)
        self.putparse.add_argument(
            name="log", type=str, required=False)
        self.putparse.add_argument(
            name="artifact", type=dict, required=False)
        self.putparse.add_argument(
            name="archived", type=bool, required=False)
        self.putparse.add_argument(
            name="type", type=str, required=False)

        super(ArtifactImportResource, self).__init__()

    def get(self, artifact_import_id):
        api_key = request.headers.get('X-Api-Key')
        verify_api_key(api_key, config_name)

        artifact_import = db.session.query(ArtifactImport).filter(
            ArtifactImport.id == artifact_import_id).first()
        if not artifact_import:
            abort(404, description="invalid artifact import ID")

        response = jsonify(ArtifactImportSchema().dump(artifact_import))
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

    def put(self, artifact_import_id):
        """
        Allows the importer to push an artifact_import's status and
        data to us.
        """
        api_key = request.headers.get('X-Api-Key')
        verify_api_key(api_key, config_name)

        artifact_import = db.session.query(ArtifactImport).filter(
            ArtifactImport.id == artifact_import_id).first()
        if not artifact_import:
            abort(404, description="invalid artifact import ID")

        args = self.putparse.parse_args()
        if not args or len(args) < 1:
            abort(400, description="no properties sent to modify")
        if args["userid"] and artifact_import.owner_id != args["userid"]:
            abort(403, description="userid %r does not own this artifact" % (args["userid"],))
        if args["userid"]:
            if args["archived"] == None or len(vars(args)) > 2:
                abort(400, description="userid %r may only change archived status" % (args["userid"],))
        if args["status"] != None and args["status"] not in ARTIFACT_IMPORT_STATUSES:
            abort(400, description="invalid status (must be one of %s)" % (
                ",".join(ARTIFACT_IMPORT_STATUSES)))
        if args["phase"] != None and args["phase"] not in ARTIFACT_IMPORT_PHASES:
            abort(400, description="invalid phase (must be one of %s)" % (
                ",".join(ARTIFACT_IMPORT_PHASES)))

        if args["mtime"]:
            args["mtime"] = dateutil.parser.parse(args["mtime"])
        else:
            args["mtime"] = datetime.datetime.now()
        artifact = args.get("artifact",None)
        del args["artifact"]

        for (k,v) in args.items():
            if v is None:
                continue
            setattr(artifact_import,k,v)
        db.session.commit()

        if "status" in args and args["status"] in ("completed","failed"):
            importer_schedule = db.session.query(ImporterSchedule)\
              .filter(ImporterSchedule.artifact_import_id == artifact_import_id).first()
            db.session.delete(importer_schedule)
            db.session.commit()

            LOG.debug("artifact import status %r; scheduling" % (args["status"],))
            threading.Thread(target=schedule_import,name="schedule_import").start()

        if args["status"] == "completed" and args["phase"] == "done":
            if artifact:
                artifact = object_from_json(db.session,Artifact,artifact,skip_ids=None)
                db.session.add(artifact)
                try:
                    db.session.commit()
                    db.session.refresh(artifact)
                    artifact_import.artifact = artifact
                    db.session.commit()
                    response = jsonify(dict(id=artifact.id))
                    response.status_code = 200
                    return response
                except sqlalchemy.exc.IntegrityError:
                    #psycopg2.errors.UniqueViolation:
                    traceback.print_exc()
                    artifact_import.status = "failed"
                    artifact_import.message = "failed to upload artifact from importer (duplicate)"
                    db.session.commit()
                    abort(400,description="duplicate artifact")
                except:
                    traceback.print_exc()
                    artifact_import.status = "failed"
                    artifact_import.message = "failed to upload artifact from importer"
                    db.session.commit()
                    abort(500)
            else:
                artifact_import.status = "failed"
                artifact_import.message = "no artifact returned from importer"
                db.session.commit()
                abort(400, description="must provide artifact on successful import")

        return Response(status=200)
