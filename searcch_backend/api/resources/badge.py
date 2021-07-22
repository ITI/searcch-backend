
from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.auth import verify_api_key
from searcch_backend.models.model import Badge
from searcch_backend.models.schema import BadgeSchema
from flask import abort, jsonify, request
from flask_restful import reqparse, Resource
import sqlalchemy
from sqlalchemy import func, asc, desc, sql, and_, or_
import logging

LOG = logging.getLogger(__name__)

class BadgeResourceRoot(Resource):

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument(name="page",
                                   type=int,
                                   required=False,
                                   default=1,
                                   help="page number for paginated results")
        self.reqparse.add_argument(name="all",
                                   type=bool,
                                   required=False,
                                   default=False,
                                   help="disable pagination; return all badges")
        self.reqparse.add_argument(name="verified",
                                   type=bool,
                                   required=False,
                                   default=False,
                                   help="only display verified, sanitized badges")
        super(BadgeResourceRoot, self).__init__()

    def get(self):
        args = self.reqparse.parse_args()
        page = args["page"]
        all_badges = args["all"]
        verified = args["verified"]

        query = db.session.query(Badge)
        if verified:
            query = query.filter(Badge.verified == True)
        query = query.order_by(asc(Badge.title))
        if all_badges:
            badges = query.all()
        else:
            badges = query.paginate(page=page, error_out=False, max_per_page=20).items

        response = jsonify({"badges": BadgeSchema(many=True).dump(badges)})
        response.status_code = 200
        return response

        response = jsonify({
            "badges": badges
            })
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.status_code = 200
        return response


class BadgeResource(Resource):

    def get(self, badge_id):
        badge = db.session.query(Badge).filter(
            Badge.id == badge_id).first()
        if not badge:
            abort(404, description="invalid badge ID")

        response = jsonify(BadgeSchema().dump(badge))
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.status_code = 200
        return response

    def post(self):
        pass
