
from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.auth import verify_api_key
from searcch_backend.models.model import Organization
from searcch_backend.models.schema import OrganizationSchema
from flask import abort, jsonify, request
from flask_restful import reqparse, Resource
import sqlalchemy
from sqlalchemy import func, asc, desc, sql, and_, or_
import logging

LOG = logging.getLogger(__name__)

class OrganizationListAPI(Resource):
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
                                   help="disable pagination; return all organizations")
        self.reqparse.add_argument(name="verified",
                                   type=bool,
                                   required=False,
                                   default=False,
                                   help="only display verified, sanitized organizations")
        super(OrganizationListAPI, self).__init__()

    def get(self):
        args = self.reqparse.parse_args()
        page = args["page"]
        all_orgs = args["all"]
        verified = args["verified"]

        query = db.session.query(Organization)
        if verified:
            query = query.filter(Organization.verified == True)
        query = query.order_by(asc(Organization.name))
        if all_orgs:
            organizations = query.all()
        else:
            organizations = query.paginate(page=page, error_out=False, max_per_page=20).items

        response = jsonify({"organizations": OrganizationSchema(many=True).dump(organizations)})
        response.status_code = 200
        return response

        response = jsonify({
            "organizations": organizations
            })
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.status_code = 200
        return response


class OrganizationAPI(Resource):

    def get(self, org_id):
        organization = db.session.query(Organization).filter(
            Organization.id == org_id).first()
        if not organization:
            abort(404, description="invalid organization ID")

        response = jsonify(OrganizationSchema().dump(organization))
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.status_code = 200
        return response
