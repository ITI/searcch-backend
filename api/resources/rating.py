# logic for /ratings

from api.app import db
from api.common.auth import *
from models.model import *
from models.schema import *
from flask import abort, jsonify, request, make_response, Blueprint
from flask_restful import reqparse, Resource, fields, marshal


class RatingAPI(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument(name='token',
                                   type=str,
                                   required=True,
                                   default='',
                                   location='form',
                                   help='missing SSO token from auth provider in post request')
        self.reqparse.add_argument(name='api_key',
                                   type=str,
                                   required=True,
                                   default='',
                                   location='form',
                                   help='missing API secret key in post request')
        self.reqparse.add_argument(name='userid',
                                   type=int,
                                   required=True,
                                   location='form',
                                   help='missing ID of user rating the artifact')
        self.reqparse.add_argument(name='rating',
                                   type=int,
                                   required=True,
                                   choices=(0, 1, 2, 3, 4, 5),
                                   location='form',
                                   help='missing rating for artifact')

    def post(self, artifact_id):
        args = self.reqparse.parse_args()
        api_key = args['api_key']
        sso_token = args['token']
        user_id = args['userid']
        rating = args['rating']

        # verify session credentials
        verify_api_key(api_key)
        if not verify_token(sso_token):
            abort(401, "no active login session found. please login to continue")

        # check for valid artifact id
        artifact = db.session.query(Artifact).filter(
            Artifact.id == artifact_id).first()
        if not artifact:
            abort(400, description='invalid artifact ID')

        # add new rating to the database
        # TODO: insert rating without explictly providing value for primary_key
        # new_rating = ArtifactRatings(id=1, user_id=user_id, artifact_id=artifact_id, rating=rating)
        new_rating = ArtifactRatings(user_id=user_id, artifact_id=artifact_id, rating=rating)
        db.session.add(new_rating)
        db.session.commit()

        response = jsonify({"message": "added new rating"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

    def put(self, artifact_id):
        args = self.reqparse.parse_args()
        api_key = args['api_key']
        sso_token = args['token']
        user_id = args['userid']
        rating = args['rating']

        # verify session credentials
        verify_api_key(api_key)
        if not verify_token(sso_token):
            abort(401, "no active login session found. please login to continue")

        rating = db.session.query(ArtifactRatings).filter(
            ArtifactRatings.user_id == user_id, ArtifactRatings.artifact_id == artifact_id).first().update(dict(rating=rating))
        db.session.commit()

        response = jsonify({"message": "updated rating"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

    def delete(self, artifact_id):
        args = self.reqparse.parse_args()
        api_key = args['api_key']
        sso_token = args['token']
        user_id = args['userid']

        # verify session credentials
        verify_api_key(api_key)
        if not verify_token(sso_token):
            abort(401, "no active login session found. please login to continue")

        # # check for valid artifact id
        # artifact = db.session.query(Artifact).filter(
        #     Artifact.id == artifact_id).first()
        # if not artifact:
        #     abort(400, description='invalid artifact ID')

        rating = db.session.query(ArtifactRatings).filter(
            ArtifactRatings.user_id == user_id, ArtifactRatings.artifact_id == artifact_id).first()
        if rating:
            db.session.delete(rating)
            db.session.commit()
            response = jsonify({"message": "deleted rating"})
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.status_code = 200
            return response
        else:
            abort(404, description="user has not rated this artifact")
