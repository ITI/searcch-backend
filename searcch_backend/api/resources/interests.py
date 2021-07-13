from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.auth import (verify_api_key, verify_token)
from searcch_backend.models.model import *
from searcch_backend.models.schema import *
from flask import abort, jsonify, request, make_response, Blueprint
from flask_restful import reqparse, Resource, fields, marshal
import logging

LOG = logging.getLogger(__name__)


class InterestsListAPI(Resource):
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
        super(InterestsListAPI, self).__init__()
        
    def get(self):
        verify_api_key(request)

        research_interests = [row.research_interests for row in db.session.query(Person.research_interests).distinct() if row.research_interests is not None]

        if not research_interests:
            response = jsonify(
                {"message": "No research interests present"})
        else:
            response = jsonify({
                "research_interests" : research_interests
            })

        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response
