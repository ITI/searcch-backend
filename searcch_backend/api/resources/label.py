from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.auth import (verify_api_key, verify_token)
from flask import abort, jsonify, request, make_response, Blueprint
from flask_restful import reqparse, Resource, fields, marshal
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
        self.reqparse.add_argument(name="artifact_id",
                                   type=int,
                                   required=True,
                                   help="Artifact id required for label")
        self.reqparse.add_argument(name='label_url',
                                   type=str,
                                   required=True,
                                   help='missing label url')
        self.reqparse.add_argument(name='label_id',
                                   type=str,
                                   required=True,
                                   help='missing label id')
    
    

    def post(self, artifact_id):
        verify_api_key(request)
        login_session = verify_token(request)

        args = self.reqparse.parse_args()
        print("Args ==", args)
        request_entry = Labels(
                artifact_id=args["artifact_id"],
                label_url=args["label_url"],
                label_id =args["label_id"],
        )
        existing_row = db.session.query(Labels).filter_by(label_id=args['label_id'], artifact_id=args['artifact_id']).first()
        if existing_row:
                existing_row.label_url = args['label_url']
        else:
                db.session.add(request_entry)

        db.session.commit()
        response = jsonify({
                "status": 200,
                "message": "Request submitted successfully",
                "request": LabelSchema().dump(request_entry)
        })
        return response
        