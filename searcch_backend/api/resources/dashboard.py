# logic for /rating

from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.auth import *
from searcch_backend.models.model import *
from searcch_backend.models.schema import *
from flask import abort, jsonify, request, url_for
from flask_restful import reqparse, Resource
from sqlalchemy import func, desc, sql


class UserDashboardAPI(Resource):
    """ 
    UserDashboardAPI
    API to: 
        - generate the dashboard content specific to the current logged-in user

    Dashboard contains:
        - artifacts owned by the user
        - reviews and ratings provided by the user
        - past searches made by the user
    """
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument(name='token',
                                   type=str,
                                   required=True,
                                   default='',
                                   help='missing SSO token from auth provider in post request')
        self.reqparse.add_argument(name='userid', 
                                   type=int, required=True, help='missing user ID')

        super(UserDashboardAPI, self).__init__()

    def get(self):
        args = self.reqparse.parse_args()
        user_id = args['userid']

        # verify credentials
        api_key = request.headers.get('X-API-Key')
        verify_api_key(api_key, config_name)
        if config_name == 'production':
            sso_token = args['token']
            if not verify_token(sso_token):
                abort(401, "no active login session found. please login to continue")

        # get user details from the logged-in session
        active_login_session = db.session.query(Sessions).filter(
            Sessions.sso_token == sso_token).first()
        if active_login_session.user_id != user_id:
                abort(401, "cannot edit profile for another user")

        # get user's personal information
        user = db.session.query(User).filter(User.id == user_id).first()

        # artifacts owned by the logged-in user
        artifact_schema = ArtifactSchema(many=True, exclude=('meta', 'tags', 'files', 'affiliations', 'relationships'))
        owned_artifacts = db.session.query(Artifact).filter(Artifact.owner_id == user.id)

        response = jsonify({
            "user": UserSchema().dump(user),
            "owned_artifacts": artifact_schema.dump(owned_artifacts)
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response
