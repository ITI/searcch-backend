
from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.auth import verify_api_key
from searcch_backend.models.model import RecurringVenue
from searcch_backend.models.schema import RecurringVenueSchema
from flask import abort, jsonify, request
from flask_restful import reqparse, Resource
import sqlalchemy
from sqlalchemy import func, asc, desc, sql, and_, or_
import logging

LOG = logging.getLogger(__name__)

class RecurringVenueResourceRoot(Resource):

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
                                   help="disable pagination; return all recurring_venues")
        self.reqparse.add_argument(name="verified",
                                   type=bool,
                                   required=False,
                                   default=False,
                                   help="only display verified, sanitized recurring_venues")
        super(RecurringVenueResourceRoot, self).__init__()

    def get(self):
        args = self.reqparse.parse_args()
        page = args["page"]
        all_recurring_venues = args["all"]
        verified = args["verified"]

        query = db.session.query(RecurringVenue)
        if verified:
            query = query.filter(RecurringVenue.verified == True)
        query = query.order_by(asc(RecurringVenue.title))
        if all_recurring_venues:
            recurring_venues = query.all()
        else:
            recurring_venues = query.paginate(page=page, error_out=False, max_per_page=20).items

        response = jsonify({"recurring_venues": RecurringVenueSchema(many=True).dump(recurring_venues)})
        response.status_code = 200
        return response

        response = jsonify({
            "recurring_venues": recurring_venues
            })
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.status_code = 200
        return response


class RecurringVenueResource(Resource):

    def get(self, recurring_venue_id):
        recurring_venue = db.session.query(RecurringVenue).filter(
            RecurringVenue.id == recurring_venue_id).first()
        if not recurring_venue:
            abort(404, description="invalid recurring_venue ID")

        response = jsonify(RecurringVenueSchema().dump(recurring_venue))
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.status_code = 200
        return response

    def post(self):
        pass
