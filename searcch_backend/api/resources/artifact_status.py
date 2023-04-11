# logic for /artifacts

from searcch_backend.api.app import db
from searcch_backend.models.model import *
from searcch_backend.models.schema import *
from searcch_backend.api.common.stats import StatsResource
from flask import jsonify, request
from flask_restful import reqparse, Resource
from searcch_backend.api.common.auth import (verify_api_key, has_api_key, has_token, verify_token)
import logging
from searcch_backend.api.ticket_creation.antAPI.client.auth import AntAPIClientAuthenticator
from searcch_backend.api.ticket_creation.antAPI.client.trac import (
       antapi_trac_ticket_status,
)
from searcch_backend.api.ticket_creation.antapi_client_conf import AUTH

LOG = logging.getLogger(__name__)


class ArtifactRequestStatusAPI(Resource):
    def __init__(self):
        # self.reqparse = reqparse.RequestParser()
        # self.reqparse.add_argument(name='artifact_group_id',
        #                            type=int,
        #                            required=True,
        #                            help='missing artifact_group_id in query string')
        super(ArtifactRequestStatusAPI, self).__init__()

    def get(self, artifact_group_id):
        # args = self.reqparse.parse_args()
        if has_api_key(request):
            verify_api_key(request)
        
        user_id = None
        if has_token(request):
            login_session = verify_token(request)
            user_id = login_session.user_id

        ticket_status = "unrequested"

        if artifact_group_id and user_id:
            db_response = db.session.query(ArtifactRequests.ticket_id).filter(artifact_group_id == ArtifactRequests.artifact_group_id).filter(user_id == ArtifactRequests.requester_user_id).first()

            if db_response:
                ticket_id = db_response[0]

                if ticket_id == -1: # -1 is the dummy ticket_id value used when testing the requested and released flow(see artifact_request.py and the code block where the ticket is filed)
                    ticket_status = "released"
                elif ticket_id == -2: # -2 is the dummy ticket_id value used when testing the requested but not released flow (see artifact_request.py and the code block where the ticket is filed)
                    ticket_status = "new"
                else : # regular user flow
                    auth = AntAPIClientAuthenticator(**AUTH)
                    ticket_status = antapi_trac_ticket_status(auth, ticket_id)

        response = jsonify({
            "ticket_status": ticket_status
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response
