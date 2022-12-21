import datetime
import dateutil.parser
import logging
import sys
import threading
import traceback
import math

import sqlalchemy
from sqlalchemy import asc, desc, sql, not_, or_
from flask import abort, jsonify, request, Response, Blueprint
from flask_restful import reqparse, Resource, fields, marshal

from searcch_backend.models.model import (
    ArtifactImport, ImporterSchedule, ImporterInstance,
    ArtifactGroup, Artifact, User, Person,
    ARTIFACT_IMPORT_TYPES,
    ARTIFACT_IMPORT_STATUSES, ARTIFACT_IMPORT_PHASES )
from searcch_backend.models.schema import (
    ArtifactImportSchema )
from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.auth import (verify_api_key, verify_token, has_token)
from searcch_backend.api.common.importer import schedule_import
from searcch_backend.api.common.sql import object_from_json

LOG = logging.getLogger(__name__)

class ArtifactImportResourceRoot(Resource):

    def __init__(self):
        self.postparse = reqparse.RequestParser()
        self.postparse.add_argument(
            name="url", type=str, required=True, nullable=False,
            help="Artifact source URL required")
        self.postparse.add_argument(
            name="importer_module_name", type=str, required=False,
            help="A specific importer name to use")
        self.postparse.add_argument(
            name="nofetch", type=bool, required=False, default=False,
            help="If True, do not fetch artifact files.")
        self.postparse.add_argument(
            name="noextract", type=bool, required=False, default=False,
            help="If True, do not extract additional metadata (e.g. keywords) from artifact content and files.")
        self.postparse.add_argument(
            name="noremove", type=bool, required=False, default=False,
            help="If True, do not removed fetched artifact content.")
        self.postparse.add_argument(
            name="type", type=str, required=False,
            help="A specific type of artifact; defaults to `unknown`; one of (%s)" % (
                ",".join(ARTIFACT_IMPORT_TYPES)))

        self.getparse = reqparse.RequestParser()
        self.getparse.add_argument(
            name="status", type=str, required=False, location="args",
            help="status must be one of pending,scheduled,running,completed,failed")
        self.getparse.add_argument(
            name="archived", type=int, required=False, location="args",
            default=0, help="if 1, show archived imports")
        self.getparse.add_argument(
            name="allusers", type=int, required=False, default=0, location="args",
            help="if set 1, and if caller is authorized, show all user imports")
        self.getparse.add_argument(
            name="owner", type=str, required=False, location="args",
            help="if set, filter by user email and name")
        self.getparse.add_argument(
            name="page", type=int, required=False,
            help="page number for paginated results")
        self.getparse.add_argument(
            name="items_per_page", type=int, required=False, default=20,
            help="results per page if paginated")
        self.getparse.add_argument(
            name="sort", type=str, required=False, default="id",
            choices=("id", "url", "ctime", "status", "artifact_id"),
            help="bad sort field: {error_msg}")
        self.getparse.add_argument(
            name="sort_desc", type=int, required=False, default=1,
            help="if set True, sort descending, else ascending")

        super(ArtifactImportResourceRoot, self).__init__()

    def get(self):
        """
        Get a list of artifact imports.  Filtered by session.user_id,
        status (optional) (pending,scheduled,running,completed,failed),
        and archived state.
        """
        verify_api_key(request)
        login_session = verify_token(request)

        args = self.getparse.parse_args()
        status = args["status"]

        artifact_imports = db.session.query(ArtifactImport)\
          .filter(True if login_session.is_admin and args["allusers"] \
                      else ArtifactImport.owner_id == login_session.user_id)
        if status:
            artifact_imports = artifact_imports.filter(ArtifactImport.status == status)
        if not args["archived"]:
            artifact_imports = artifact_imports.filter(ArtifactImport.archived == False)
        if args["owner"]:
            owner_cond = "%" + args["owner"] + "%"
            artifact_imports = artifact_imports.\
              join(User, ArtifactImport.owner_id == User.id).\
              join(Person, User.person_id == Person.id)
            artifact_imports = artifact_imports.\
              filter(or_(Person.name.ilike(owner_cond),
                         Person.email.ilike(owner_cond)))
        if not args["sort"]:
            args["sort"] = "id"
        if args["sort_desc"]:
            LOG.debug("desc: desc")
            artifact_imports = artifact_imports.\
              order_by(desc(getattr(ArtifactImport,args["sort"])))
        else:
            LOG.debug("desc: asc")
            artifact_imports = artifact_imports.\
              order_by(asc(getattr(ArtifactImport,args["sort"])))

        pagination = None
        if "page" in args and args["page"]:
            if args["items_per_page"] <= 0:
                args["items_per_page"] = sys.maxsize
            pagination = artifact_imports.paginate(
                page=args["page"], error_out=False, per_page=args["items_per_page"])
            artifact_imports = pagination.items
        else:
            artifact_imports = artifact_imports.all()

        response_dict = {
            "artifact_imports": ArtifactImportSchema(
                many=True,exclude=("artifact",)).dump(artifact_imports)
        }
        if pagination:
            response_dict["page"] = pagination.page
            response_dict["total"] = pagination.total
            response_dict["pages"] = int(math.ceil(pagination.total / args["items_per_page"]))

        response = jsonify(response_dict)
        response.status_code = 200
        return response


    def post(self):
        """
        This is the primary artifact creation method.  It takes as input a URL, the uid, and possibly a specific importer to use.  It creates a temporary import session once handed off to the importer, and the frontend then polls based off the import session for completion of the import.  This is asynchronous, and returns an import session ID, if sanity checks succeed (e.g., an importer of the given name (if any) exists, rate limits are within tolerances, etc).  Note that the initial checks do *not* include URL reachability, since URLs may not all be reachable nor veriable over a basic HTTP(S) connection; the importer module must handle this case.  Finally, we cannot wait for the importer to do this reachability check, because there might be a queue of imports already being processed.
        """
        verify_api_key(request)
        login_session = verify_token(request)

        args = self.postparse.parse_args()
        if not args["url"]:
            abort(400, description="must provide non-null URL")
        if args["type"] and args["type"] not in ARTIFACT_IMPORT_TYPES:
            abort(400, description="invalid artifact type")
        elif not "type" in args or not args["type"]:
            args["type"] = "unknown"

        res = db.session.query(ArtifactImport).\
          filter(ArtifactImport.url == args["url"]).\
          filter(ArtifactImport.owner_id == login_session.user_id).\
          filter(ArtifactImport.artifact_id == None).\
          filter(not_(ArtifactImport.status.in_(["completed","failed"]))).\
          all()
        if len(res) > 0:
            abort(400, description="user_id %r already importing from %r" % (login_session.user_id,args["url"]))

        dt = datetime.datetime.now()
        ai = ArtifactImport(
            **args,owner_id=login_session.user_id,ctime=dt,mtime=dt,status="pending",
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
        verify_api_key(request)
        login_session = verify_token(request)

        artifact_import = db.session.query(ArtifactImport)\
          .filter(ArtifactImport.id == artifact_import_id)\
          .first()
        if not artifact_import:
            abort(404, description="invalid artifact import ID")
        if artifact_import.owner_id != login_session.user_id and not login_session.is_admin:
            abort(403, description="insufficient permission")

        response = jsonify(ArtifactImportSchema().dump(artifact_import))
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

    def put(self, artifact_import_id):
        """
        Allows the importer to push an artifact_import's status and
        data to us, or for a user to modify the import's state.
        """
        verify_api_key(request)
        login_session = None
        if has_token(request):
            login_session = verify_token(request)

        artifact_import = db.session.query(ArtifactImport).filter(
            ArtifactImport.id == artifact_import_id).first()
        if not artifact_import:
            abort(404, description="invalid artifact import ID")

        args = self.putparse.parse_args()
        if not args or len(args) < 1:
            abort(400, description="no properties sent to modify")
        if login_session:
            if artifact_import.owner_id != login_session.user_id:
                abort(403, description="insufficient permission to modify artifact")
            if args["archived"] == None or len(vars(args)) > 2:
                abort(400, description="user may only change archived status")
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
        artifact_json = args.get("artifact",None)
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
            if artifact_json:
                dt = datetime.datetime.now()
                if "owner" in artifact_json:
                    del artifact_json["owner"]
                if "owner_id" in artifact_json:
                    del artifact_json["owner_id"]
                artifact = None
                try:
                    artifact = object_from_json(db.session,Artifact,artifact_json,skip_primary_keys=True)
                except (TypeError, ValueError):
                    ex = sys.exc_info()[1]
                    LOG.exception(ex)
                    db.session.rollback()
                    msg = ""
                    if ex.args:
                        msg = "Internal error: %r" % (ex.args,)
                    else:
                        msg = "Internal error: %r" % (ex,)
                    db.session.refresh(artifact_import)
                    artifact_import.status = "failed"
                    artifact_import.mtime = dt
                    artifact_import.message = msg
                    db.session.add(artifact_import)
                    db.session.commit()
                    abort(500, description=msg)
                except:
                    LOG.exception(sys.exc_info()[1])
                    db.session.rollback()
                    db.session.refresh(artifact_import)
                    artifact_import.status = "failed"
                    artifact_import.mtime = dt
                    msg = "Unexpected internal error"
                    artifact_import.message = msg
                    db.session.add(artifact_import)
                    db.session.commit()
                    abort(500, description=msg)

                if artifact_import.artifact_group_id is None:
                    artifact_group = ArtifactGroup(owner_id=artifact_import.owner_id,
                                                   next_version=0)
                    artifact.artifact_group = artifact_group
                    db.session.add(artifact_group)
                else:
                    artifact.artifact_group_id = artifact_import.artifact_group_id

                artifact.owner_id = artifact_import.owner_id
                if artifact_import.parent_artifact_id:
                    artifact.parent_id = artifact_import.parent_artifact_id
                db.session.add(artifact)
                try:
                    db.session.commit()
                    db.session.refresh(artifact)
                    artifact_import.artifact = artifact
                    artifact_import.artifact_group_id = artifact.artifact_group_id
                    db.session.commit()
                    response = jsonify(dict(id=artifact.id))
                    response.status_code = 200
                    return response
                except sqlalchemy.exc.IntegrityError:
                    #psycopg2.errors.UniqueViolation:
                    ex = sys.exc_info()[1]
                    LOG.exception(ex)
                    db.session.rollback()
                    msg = "failed to upload artifact from importer (possible duplicate or malformed data)"
                    db.session.refresh(artifact_import)
                    artifact_import.status = "failed"
                    artifact_import.message = msg
                    artifact_import.mtime = dt
                    db.session.add(artifact_import)
                    db.session.commit()
                    abort(400,description=msg)
                except:
                    ex = sys.exc_info()[1]
                    LOG.exception(ex)
                    db.session.rollback()
                    msg = "failed to upload artifact from importer (unknown cause)"
                    db.session.refresh(artifact_import)
                    artifact_import.status = "failed"
                    artifact_import.message = msg
                    db.session.commit()
                    abort(500,description=msg)
            else:
                artifact_import.status = "failed"
                artifact_import.message = "no artifact returned from importer"
                db.session.commit()
                abort(400, description="must provide artifact on successful import")

        return Response(status=200)

    def delete(self, artifact_import_id):
        """
        Deletes an import if the import does not (yet) point to a completed artifact (and also deletes from importer_schedules if necessary).  If import points to a live artifact, we mark the import as archived.
        """
        verify_api_key(request)
        login_session = None
        if has_token(request):
            login_session = verify_token(request)

        artifact_import = db.session.query(ArtifactImport).filter(
            ArtifactImport.id == artifact_import_id).first()
        if not artifact_import:
            abort(404, description="invalid artifact import ID")
        if login_session:
            if artifact_import.owner_id != login_session.user_id:
                abort(403, description="insufficient permission to modify artifact_import")

        if artifact_import.artifact_id is not None:
            if artifact_import.archived:
                abort(404, description="invalid artifact import ID")
            artifact_import.archived = True
            db.session.add(artifact_import)
            db.session.commit()
            return Response(status=200)
        else:
            sched = db.session.query(ImporterSchedule).\
              filter(ImporterSchedule.artifact_import_id == artifact_import.id).\
              first()
            if sched:
                db.session.delete(sched)
            db.session.delete(artifact_import)
            db.session.commit()
            return Response(status=200)
