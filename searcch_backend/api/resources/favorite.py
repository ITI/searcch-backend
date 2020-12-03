# logic for /rating

from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.auth import *
from searcch_backend.models.model import *
from searcch_backend.models.schema import *
from flask import abort, jsonify, request, url_for, Blueprint
from flask_restful import reqparse, Resource, fields, marshal


class FavoritesListAPI(Resource):
    @staticmethod
    def generate_artifact_uri(artifact_id):
        return url_for('api.artifact', artifact_id=artifact_id)

    def get(self, user_id):
        favorite_artifacts = db.session.query(Artifact).join(
            ArtifactFavorites, Artifact.id == ArtifactFavorites.artifact_id).filter(ArtifactFavorites.user_id == user_id).all()

        artifacts = []
        for artifact in favorite_artifacts:
            result = {
                "id": artifact.id,
                "uri": FavoritesListAPI.generate_artifact_uri(artifact.id),
                "doi": artifact.url,
                "type": artifact.type,
                "title": artifact.title,
                "description": artifact.description
            }
            artifacts.append(result)

        response = jsonify({"artifacts": artifacts, "length": len(artifacts)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response


class FavoriteAPI(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        if config_name == 'production':
            self.reqparse.add_argument(name='token',
                                    type=str,
                                    required=True,
                                    default='',
                                    help='missing SSO token from auth provider in post request')
        self.reqparse.add_argument(name='api_key',
                                   type=str,
                                   required=True,
                                   default='',
                                   help='missing API secret key in post request')
        self.reqparse.add_argument(name='userid',
                                   type=int,
                                   required=True,
                                   help='missing ID of user favoriting the artifact')
        
        super(FavoriteAPI, self).__init__()

    def post(self, artifact_id):
        args = self.reqparse.parse_args()
        api_key = args['api_key']
        if config_name == 'production':
            sso_token = args['token']
        user_id = args['userid']

        # verify session credentials
        verify_api_key(api_key)
        if config_name == 'production' and not verify_token(sso_token):
            abort(401, "no active login session found. please login to continue")

        # check for valid artifact id
        artifact = db.session.query(Artifact).filter(
            Artifact.id == artifact_id).first()
        if not artifact:
            abort(400, description='invalid artifact ID')

        # add new rating to the database
        new_favorite = ArtifactFavorites(
            user_id=user_id, artifact_id=artifact_id)
        db.session.add(new_favorite)
        db.session.commit()

        response = jsonify({"message": "added artifact to favorites list"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

    def delete(self, artifact_id):
        args = self.reqparse.parse_args()
        api_key = args['api_key']
        if config_name == 'production':
            sso_token = args['token']
        user_id = args['userid']

        # verify session credentials
        verify_api_key(api_key)
        if config_name == 'production' and not verify_token(sso_token):
            abort(401, "no active login session found. please login to continue")

        existing_favorite = db.session.query(ArtifactFavorites).filter(
            ArtifactFavorites.user_id == user_id, ArtifactFavorites.artifact_id == artifact_id).first()
        if existing_favorite:
            db.session.delete(existing_favorite)
            db.session.commit()
            response = jsonify(
                {"message": "deleted artifact from favorites list"})
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.status_code = 200
            return response
        else:
            abort(
                404, description="this artifact does not exist in the user's favorites list")
