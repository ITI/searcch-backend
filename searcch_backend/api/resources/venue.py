
from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.auth import verify_api_key
from searcch_backend.models.model import Venue
from searcch_backend.models.schema import VenueSchema
from flask import abort, jsonify, request
from flask_restful import reqparse, Resource
import sqlalchemy
from sqlalchemy import func, asc, desc, sql, and_, or_
import logging

LOG = logging.getLogger(__name__)

class VenueResourceRoot(Resource):

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
                                   help="disable pagination; return all venues")
        self.reqparse.add_argument(name="verified",
                                   type=bool,
                                   required=False,
                                   default=False,
                                   help="only display verified, sanitized venues")
        super(VenueResourceRoot, self).__init__()

    def get(self):
        args = self.reqparse.parse_args()
        page = args["page"]
        all_venues = args["all"]
        verified = args["verified"]

        query = db.session.query(Venue)
        if verified:
            query = query.filter(Venue.verified == True)
        query = query.order_by(asc(Venue.title))
        if all_venues:
            venues = query.all()
        else:
            venues = query.paginate(page=page, error_out=False, max_per_page=20).items

        response = jsonify({"venues": VenueSchema(many=True).dump(venues)})
        response.status_code = 200
        return response

        response = jsonify({
            "venues": venues
            })
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.status_code = 200
        return response


class VenueResource(Resource):

    def get(self, venue_id):
        venue = db.session.query(Venue).filter(
            Venue.id == venue_id).first()
        if not venue:
            abort(404, description="invalid venue ID")

        response = jsonify(VenueSchema().dump(venue))
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.status_code = 200
        return response

    def post(self):
        pass
