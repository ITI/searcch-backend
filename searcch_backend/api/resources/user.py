# logic for /rating

from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.auth import *
from searcch_backend.models.model import *
from searcch_backend.models.schema import *
from flask import abort, jsonify, request, url_for, Blueprint
from flask_restful import reqparse, Resource, fields, marshal
from sqlalchemy import func, desc, sql


class UserProfileAPI(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument(name='token',
                                   type=str,
                                   required=True,
                                   default='',
                                   help='missing SSO token from auth provider in post request')

        super(UserProfileAPI, self).__init__()

    def get(self):
        args = self.reqparse.parse_args()
        sso_token = args['token']

        # verify session credentials
        api_key = request.headers.get('X-API-Key')
        verify_api_key(api_key)
        if not verify_token(sso_token):
            abort(401, "no active login session found. please login to continue")

        # get user id from the currently active user session
        active_login_session = db.session.query(Sessions).filter(
            Sessions.sso_token == sso_token).first()
        user_id = active_login_session.user_id

        user_schema = UserSchema()
        user = db.session.query(User).filter(User.id == user_id).first()

        # TODO: update fields to return for artifacts owned by the logged-in user
        artifact_schema = ArtifactSchema(many=True, exclude=('meta', 'tags', 'files', 'affiliations', 'relationships'))
        owned_artifacts = db.session.query(Artifact).filter(Artifact.owner_id == user.id).limit(10)

        response = jsonify({
            "user": user_schema.dump(user),
            "owned_artifacts": artifact_schema.dump(owned_artifacts)
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response
