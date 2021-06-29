# logic for /rating

from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.auth import (verify_api_key, verify_token)
from searcch_backend.models.model import *
from searcch_backend.models.schema import *
from flask import abort, jsonify, request, make_response, Blueprint
from flask_restful import reqparse, Resource, fields, marshal


class UserRatingAPI(Resource):
    def get(self, user_id, artifact_id):
        verify_api_key(request)
        login_session = verify_token(request)

        if user_id != login_session.user_id:
            abort(401, description="insufficient permission to list ratings")

        # check for valid artifact id
        artifact = db.session.query(Artifact).filter(
            Artifact.id == artifact_id).first()
        if not artifact:
            abort(400, description='invalid artifact ID')

        rating = db.session.query(ArtifactRatings.rating).filter(
            ArtifactRatings.artifact_id == artifact_id, ArtifactRatings.user_id == login_session.user_id).first()
        if not rating:
            response = jsonify(
                {"message": "the user has not rated this artifact"})
        else:
            response = jsonify({"rating": rating[0]})

        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response


class RatingAPI(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument(name='rating',
                                   type=int,
                                   required=False,
                                   choices=(0, 1, 2, 3, 4, 5),
                                   help='missing rating for artifact')

        super(RatingAPI, self).__init__()

    def post(self, artifact_id):
        verify_api_key(request)
        login_session = verify_token(request)

        args = self.reqparse.parse_args()
        rating = args['rating']

        # check for valid artifact id
        artifact = db.session.query(Artifact).filter(
            Artifact.id == artifact_id).first()
        if not artifact:
            abort(400, description='invalid artifact ID')

        # add new rating to the database
        new_rating = ArtifactRatings(
            user_id=login_session.user_id, artifact_id=artifact_id, rating=rating)
        db.session.add(new_rating)
        db.session.commit()

        response = jsonify({"message": "added new rating"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

    def put(self, artifact_id):
        verify_api_key(request)
        login_session = verify_token(request)

        args = self.reqparse.parse_args()
        rating = args['rating']

        existing_rating = db.session.query(ArtifactRatings).filter(
            ArtifactRatings.user_id == login_session.user_id, ArtifactRatings.artifact_id == artifact_id).first()
        if existing_rating:
            existing_rating.rating = rating
            db.session.commit()
            msg = "updated rating"
        else:
            new_rating = ArtifactRatings(user_id=login_session.user_id, artifact_id=artifact_id, rating=rating)
            db.session.add(new_rating)
            db.session.commit()
            msg = "added new rating"

        response = jsonify({"message": msg})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

    def delete(self, artifact_id):
        verify_api_key(request)
        login_session = verify_token(request)

        rating = db.session.query(ArtifactRatings).filter(
            ArtifactRatings.user_id == login_session.user_id, ArtifactRatings.artifact_id == artifact_id).first()
        if rating:
            db.session.delete(rating)
            db.session.commit()
            response = jsonify({"message": "deleted rating"})
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.status_code = 200
            return response
        else:
            abort(404, description="user has not rated this artifact")
