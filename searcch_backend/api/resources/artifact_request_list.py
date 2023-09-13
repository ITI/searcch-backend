# logic for /artifacts

from searcch_backend.api.app import db
from searcch_backend.models.model import *
from searcch_backend.models.schema import *
from searcch_backend.api.common.stats import StatsResource
from flask import jsonify, request
from flask_restful import reqparse, Resource
from searcch_backend.api.common.auth import (verify_api_key, has_api_key, has_token, verify_token)
import logging
from searcch_backend.api.ticket_creation.antapi_client_conf import AUTH

LOG = logging.getLogger(__name__)


class ArtifactRequestListAPI(Resource):
    def __init__(self):
        # self.reqparse = reqparse.RequestParser()
        # self.reqparse.add_argument(name='artifact_group_id',
        #                            type=int,
        #                            required=True,
        #                            help='missing artifact_group_id in query string')
        super(ArtifactRequestListAPI, self).__init__()

    # Return value: requestedArtifactIDs: keys = Artifact Request IDs for a given user; value = Corresponding title of artifact
    def get(self):
        # args = self.reqparse.parse_args()
        if has_api_key(request):
            verify_api_key(request)
        
        user_id = None
        if has_token(request):
            login_session = verify_token(request)
            user_id = login_session.user_id
        list_of_requests_tuples = []
        if user_id:
            can_admin = db.session.query(User.can_admin).filter(User.id == user_id).first()[0]

            if can_admin == True and login_session.is_admin == True:
                list_of_requests_tuples = db.session.query(Artifact.id,Artifact.title).all()
            else:
                list_of_requests_tuples = db.session.query(ArtifactRequests.artifact_group_id,Artifact.title).join(ArtifactRequests, Artifact.id == ArtifactRequests.artifact_group_id).filter(user_id == ArtifactRequests.requester_user_id).all()

        requestedArtifactIDs = {}
        for requestTuple in list_of_requests_tuples:
            requestedArtifactIDs[requestTuple[0]] = requestTuple[1]
        
        response = jsonify({
            "requestedArtifactIDs": requestedArtifactIDs
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response