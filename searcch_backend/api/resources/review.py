# logic for /review

from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.auth import (verify_api_key, verify_token)
from searcch_backend.models.model import *
from searcch_backend.models.schema import *
from datetime import datetime
from flask import abort, jsonify, request, make_response, Blueprint
from flask_restful import reqparse, Resource, fields, marshal


class ReviewListAPI(Resource):
    def get(self, artifact_id):
        verify_api_key(request)

        # check for valid artifact id
        artifact = db.session.query(Artifact).filter(
            Artifact.id == artifact_id).first()
        if not artifact:
            abort(400, description='invalid artifact ID')

        reviews = db.session.query(ArtifactReviews).filter(
            ArtifactReviews.artifact_id == artifact_id).all()
        review_schema = ArtifactReviewsSchema(many=True)
        if not reviews:
            response = jsonify(
                {"reviews": []})
        else:
            response = jsonify({"reviews": review_schema.dump(reviews)})

        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response


class ReviewAPI(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument(name='reviewid',
                                   type=int,
                                   required=False,
                                   help='missing review ID')
        self.reqparse.add_argument(name='review',
                                   type=str,
                                   required=False,
                                   help='missing review for artifact')

    def post(self, artifact_id):
        verify_api_key(request)
        login_session = verify_token(request)

        args = self.reqparse.parse_args()
        review = args['review']

        if len(review) < 1:
            abort(400, description='review cannot be empty')

        # check for valid artifact id
        artifact = db.session.query(Artifact).filter(
            Artifact.id == artifact_id).first()
        if not artifact:
            abort(400, description='invalid artifact ID')

        # check if there exists a review by same user for same artifact already
        existing_review = db.session.query(ArtifactReviews).filter(ArtifactReviews.artifact_id == artifact_id, ArtifactReviews.user_id == login_session.user_id).first()

        # if it does, update the review, else add a new review
        if existing_review:
            existing_review.review = review
            existing_review.review_time = datetime.now()
            message = "updated existing review"
        else:
            new_review = ArtifactReviews(
                user_id=login_session.user_id, artifact_id=artifact_id, review=review, review_time=datetime.now())
            db.session.add(new_review)
            message = "added new review"
        db.session.commit()

        response = jsonify({"message": message})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

    def put(self, artifact_id):
        verify_api_key(request)
        login_session = verify_token(request)

        args = self.reqparse.parse_args()
        review_id = args['reviewid']
        review = args['review']

        if len(review) < 1:
            abort(400, description='review cannot be empty')

        existing_review = db.session.query(ArtifactReviews).filter(
            ArtifactReviews.id == review_id, ArtifactReviews.user_id == login_session.user_id, ArtifactReviews.artifact_id == artifact_id).first()
        if not existing_review:
            abort(400, description='incorrect params passed')
        existing_review.review = review
        db.session.commit()

        response = jsonify({"message": "updated review"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

    def delete(self, artifact_id):
        verify_api_key(request)
        login_session = verify_token(request)

        args = self.reqparse.parse_args()
        review_id = args['reviewid']

        existing_review = db.session.query(ArtifactReviews).filter(
            ArtifactReviews.id == review_id, ArtifactReviews.user_id == login_session.user_id, ArtifactReviews.artifact_id == artifact_id).first()
        if existing_review:
            db.session.delete(existing_review)
            db.session.commit()
            response = jsonify({"message": "deleted review"})
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.status_code = 200
            return response
        else:
            abort(404, description="invalid review ID")
