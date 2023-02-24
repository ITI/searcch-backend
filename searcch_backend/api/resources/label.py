from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.auth import verify_api_key
from flask import abort, jsonify, request
from flask_restful import reqparse, Resource
import sqlalchemy
from sqlalchemy import func, asc, desc, sql, and_, or_
import logging
from searcch_backend.models.model import *
from searcch_backend.models.schema import *
from bs4 import BeautifulSoup
import copy
import json
from datetime import datetime

LOG = logging.getLogger(__name__)

class LabelsResource(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument(name='researchers',
                                   type=str,
                                   required=True,
                                   help='missing researchers')
        self.reqparse.add_argument(name="artifact_id",
                                   type=int,
                                   required=True,
                                   help="Artifact id required for label")
    
    

    def post(self):
        verify_api_key(request)
        login_session = verify_token(request)

        args = self.reqparse.parse_args()
        request_entry = Labels(
                artifact_id=args["artifact_id"],
                label_url=args["label_url"],
        )
        
        db.session.add(request_entry)
        db.session.commit()
        response = jsonify({
                "status": 200,
                "message": "Request submitted successfully",
                "request": LabelSchema().dump(request_entry)
        })
        return response
        