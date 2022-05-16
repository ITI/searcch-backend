from datetime import date, datetime
import json
from urllib import response
from sqlalchemy.exc import IntegrityError
from searcch_backend.api.app import db, config_name, mail
from searcch_backend.api.common.auth import (verify_api_key, verify_token)
from searcch_backend.models.model import *
from searcch_backend.models.schema import *
from flask import abort, jsonify, request, make_response, Blueprint, render_template
from flask_restful import reqparse, Resource, fields, marshal, inputs
from flask_sendmail import Message
import math
import sys

class OwnershipRequestsAPI(Resource):
    def __init__(self):
        self.postparse = reqparse.RequestParser()

        self.postparse.add_argument(name='user_id',
                            type=int,
                            required=True,
                            help='missing user_id for ownership request')
        self.postparse.add_argument(name='artifact_id',
                                   type=int,
                                   required=True,
                                   help='missing artifact_id for ownership request')
        self.postparse.add_argument(name='message',
                                   type=str,
                                   required=True,
                                   help='missing ownership request message')
        
        self.getparse = reqparse.RequestParser()
        self.getparse.add_argument(name='user_id',
                                   type=int,
                                   required=False,
                                   help='missing user_id for ownership request')
        self.getparse.add_argument(name='artifact_id',
                                   type=int,
                                   required=False,
                                   help='missing artifact_id for ownership request')
        self.getparse.add_argument(name='pending',
                                   type=inputs.boolean,
                                   required=False,
                                   help='missing pending value for ownership request') 
        self.getparse.add_argument(name='approved',
                                   type=inputs.boolean,
                                   required=False,
                                   help='missing approved value for ownership request')    
        self.getparse.add_argument(name="page", type=int, required=False,
                                    help="page number for paginated results")
        self.getparse.add_argument(name="items_per_page", type=int, required=False, default=20,
                                    help="results per page if paginated")                                                                                    
        super(OwnershipRequestsAPI, self).__init__()

    def post(self):
        verify_api_key(request)
        login_session = verify_token(request)

        if not login_session.is_admin:
            abort(403, description='unauthorized access, needs admin privileges')

        args = self.postparse.parse_args()
        artifact_id = args['artifact_id']

        # check for valid artifact id
        artifact = db.session.query(Artifact).filter(
            Artifact.id == artifact_id).first()
        if not artifact:
            abort(400, description='invalid artifact ID')

        # add new rating to the database
        new_ownership_request = RequestArtifactOwnership(
            user_id=args['user_id'], artifact_id=artifact_id, message=args['message'], ctime=datetime.now())
        db.session.add(new_ownership_request)
        
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            abort(400, description='ownership request already present')
        
        # Send mail to raise approval request

        msg = Message('Claim artifact approval request for Artifact id: {}'.format(str(artifact_id)),
                sender="searcch.hub@cyberexperimentation.org",
                recipients=["insertEmailHere@example.com"])

        msg.html = render_template('email.html')

        mail.send(msg)

        # Send response
        response = jsonify({"message": "created a new ownership request, email sent"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

    def get(self):
        verify_api_key(request)
        login_session = verify_token(request)
        
        args = self.getparse.parse_args()
        user_id = args['user_id']
        artifact_id = args['artifact_id']
        pending = args['pending']
        approved = args['approved']
        page = args['page']
        items_per_page = args['items_per_page']

        ownership_requests_query = db.session.query(RequestArtifactOwnership)

        #if not admin default to current user
        if not login_session.is_admin:
            user_id = login_session.user_id

        if user_id:
            ownership_requests_query = ownership_requests_query.filter(RequestArtifactOwnership.user_id == user_id)
        
        if artifact_id:
            ownership_requests_query = ownership_requests_query.filter(RequestArtifactOwnership.artifact_id == artifact_id)

        if args['pending'] is not None:
            ownership_requests_query = ownership_requests_query.filter(RequestArtifactOwnership.pending == pending)

        if args['approved'] is not None:
            ownership_requests_query = ownership_requests_query.filter(RequestArtifactOwnership.approved == approved)
        
        if page:
            if not items_per_page:
                items_per_page = sys.maxsize
            ownership_requests_query_paginated = ownership_requests_query.paginate(error_out=True, page= page, per_page = items_per_page)
            response = jsonify({
                "page": page,
                "items_per_page": items_per_page,
                "total": ownership_requests_query_paginated.total,
                "pages": int(math.ceil(ownership_requests_query_paginated.total / items_per_page)),
                "ownership_requests": RequestArtifactOwnershipSchema(many=True).dump(ownership_requests_query_paginated.items)
            })
        else:
            ownership_requests_query_unpaginated = ownership_requests_query.all()
            response = jsonify({"ownership_requests": RequestArtifactOwnershipSchema(many=True).dump(ownership_requests_query_unpaginated)})

        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

class OwnershipRequestAPI(Resource):
    def __init__(self):
        self.putparse = reqparse.RequestParser()
        self.putparse.add_argument(name='approved',
                                    type=inputs.boolean,
                                    required=True,
                                    help='missing approved for ownership request')
        self.putparse.add_argument(name='approval_message',
                                    type=str,
                                    required=True,
                                    help='missing approval message for ownership request')

    def get(self, ownership_request_id):
        verify_api_key(request)
        verify_token(request)

        result = db.session.query(RequestArtifactOwnership).filter(RequestArtifactOwnership.id == ownership_request_id).first()
        
        if not result:
            abort(400, description='invalid request ID')
        else:
            response = jsonify(RequestArtifactOwnershipSchema().dump(result))
        
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

    def put(self, ownership_request_id):
        verify_api_key(request)
        login_session = verify_token(request)

        args = self.putparse.parse_args()

        approved = args['approved']
        approval_message = args['approval_message']

        if not login_session.is_admin:
            abort(401, description="insufficient permission to modify ownership request")

        result = db.session.query(RequestArtifactOwnership).filter(RequestArtifactOwnership.id == ownership_request_id).first()
        
        if not result:
            abort(400, description='invalid request ID')
        else:
            result.pending = False
            result.approved = approved
            result.approval_message = approval_message
            result.approving_user_id = login_session.user_id
            result.approval_time = datetime.now()
            db.session.commit()
            response = jsonify({"message": "ownership request modified", "ownership_request": RequestArtifactOwnershipSchema().dump(result)})
        
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response
