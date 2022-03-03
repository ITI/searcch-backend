# logic for /rating

from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.auth import (verify_api_key, verify_token)
from searcch_backend.api.common.sql import object_from_json
from searcch_backend.models.model import *
from searcch_backend.models.schema import *
from flask import abort, jsonify, request, url_for, Blueprint
from flask_restful import reqparse, Resource, fields, marshal
from sqlalchemy import func, desc, asc, sql, or_
import sqlalchemy
import sys
import logging
import datetime
import math


LOG = logging.getLogger(__name__)

class SessionResourceRoot(Resource):

    def __init__(self):
        self.getparse = reqparse.RequestParser()
        self.getparse.add_argument(
            name="is_admin", type=int, required=False,
            help="if 1, show only admin-on sessions")
        self.getparse.add_argument(
            name="can_admin", type=int, required=False,
            help="if 1, show only sessions by users who could have admin privileges")
        self.getparse.add_argument(
            name="allusers", type=int, required=False, default=0, location="args",
            help="if set 1, and if caller is authorized, show all user artifacts")
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
            choices=("id", "expires_on", "is_admin"),
            help="bad sort field: {error_msg}")
        self.getparse.add_argument(
            name="sort_desc", type=int, required=False, default=1,
            help="if set True, sort descending, else ascending")

        super(SessionResourceRoot, self).__init__()

    def get(self):
        verify_api_key(request)
        login_session = verify_token(request)

        args = self.getparse.parse_args()

        sessions = db.session.query(Sessions).\
          filter(True if login_session.is_admin and args["allusers"] \
                      else Sessions.user_id == login_session.user_id).\
          filter(Sessions.expires_on > datetime.datetime.now())
        if args["is_admin"] is not None:
            sessions = sessions.\
              filter(Sessions.is_admin == bool(args["is_admin"]))
        sessions = sessions.\
          join(User, Sessions.user_id == User.id).\
          join(Person, User.person_id == Person.id)
        if args["owner"]:
            owner_cond = "%" + args["owner"] + "%"
            sessions = sessions.\
              filter(or_(Person.name.ilike(owner_cond),
                         Person.email.ilike(owner_cond)))
        if args["can_admin"] is not None:
            sessions = sessions.\
              filter(User.can_admin == bool(args["can_admin"]))
        if not args["sort"]:
            args["sort"] = "id"
        if args["sort_desc"]:
            sessions = sessions.\
              order_by(desc(getattr(Sessions,args["sort"])))
        else:
            sessions = sessions.\
              order_by(asc(getattr(Sessions,args["sort"])))

        pagination = None
        if "page" in args and args["page"]:
            if args["items_per_page"] <= 0:
                args["items_per_page"] = sys.maxsize
            pagination = sessions.paginate(
                page=args["page"], error_out=False, per_page=args["items_per_page"])
            sessions = pagination.items
        else:
            sessions = sessions.all()

        # Handle can_admin securely.
        # XXX: there has to be a way for marshmallow to include excluded fields
        # based on context, but I just don't have time right now.
        tmplist = []
        for s in sessions:
            ts = SessionsSchema().dump(s)
            if login_session.is_admin or login_session.user_id == s.user.id:
                ts["user"]["can_admin"] = s.user.can_admin
            tmplist.append(ts)

        response_dict = {
            "sessions": tmplist
        }
        if pagination:
            response_dict["page"] = pagination.page
            response_dict["total"] = pagination.total
            response_dict["pages"] = int(math.ceil(pagination.total / args["items_per_page"]))
            
        response = jsonify(response_dict)

        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response


class SessionResource(Resource):

    def __init__(self):
        super(SessionResource, self).__init__()

    def delete(self, session_id):
        verify_api_key(request)
        login_session = verify_token(request)

        session = db.session.query(Sessions).\
          filter(Sessions.id == session_id).\
          first()
        if not session:
            abort(404, description="session not found")
        if not session.id == session_id \
          and not login_session.is_admin:
            abort(401, description="unauthorized")

        db.session.delete(session)
        db.session.commit()

        response = jsonify({ "message": "session %r deleted" % (session_id,) })
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response
