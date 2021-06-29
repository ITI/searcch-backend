# logic for /rating

from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.auth import (verify_api_key, verify_token)
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

    def get(self):
        verify_api_key(request)
        login_session = verify_token(request)

        # artifacts owned by the logged-in user
        artifact_schema = ArtifactSchema(many=True, exclude=('meta', 'tags', 'files', 'affiliations', 'relationships'))
        owned_artifacts = db.session.query(Artifact).filter(Artifact.owner_id == login_session.user_id)

        response = jsonify({
            "user": UserSchema().dump(user),
            "owned_artifacts": artifact_schema.dump(owned_artifacts)
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response
