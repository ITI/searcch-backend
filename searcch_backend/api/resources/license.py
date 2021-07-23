
from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.auth import verify_api_key
from searcch_backend.models.model import License
from searcch_backend.models.schema import LicenseSchema
from flask import abort, jsonify, request
from flask_restful import reqparse, Resource
import sqlalchemy
from sqlalchemy import func, asc, desc, sql, and_, or_
import logging

LOG = logging.getLogger(__name__)

class LicenseResourceRoot(Resource):

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
                                   help="disable pagination; return all licenses")
        self.reqparse.add_argument(name="verified",
                                   type=bool,
                                   required=False,
                                   default=False,
                                   help="only display verified, sanitized licenses")
        super(LicenseResourceRoot, self).__init__()

    def get(self):
        args = self.reqparse.parse_args()
        page = args["page"]
        all_licenses = args["all"]
        verified = args["verified"]

        query = db.session.query(License)
        if verified:
            query = query.filter(License.verified == True)
        query = query.order_by(asc(License.long_name))
        if all_licenses:
            licenses = query.all()
        else:
            licenses = query.paginate(page=page, error_out=False, max_per_page=20).items

        response = jsonify({"licenses": LicenseSchema(many=True).dump(licenses)})
        response.status_code = 200
        return response

        response = jsonify({
            "licenses": licenses
            })
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.status_code = 200
        return response


class LicenseResource(Resource):

    def get(self, license_id):
        license = db.session.query(License).filter(
            License.id == license_id).first()
        if not license:
            abort(404, description="invalid license ID")

        response = jsonify(LicenseSchema().dump(license))
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.status_code = 200
        return response

    def post(self):
        pass
