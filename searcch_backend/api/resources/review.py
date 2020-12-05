# logic for /review

from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.auth import *
from searcch_backend.models.model import *
from searcch_backend.models.schema import *
from datetime import datetime
from flask import abort, jsonify, request, make_response, Blueprint
from flask_restful import reqparse, Resource, fields, marshal


class ReviewListAPI(Resource):
    def get(self, artifact_id):
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
                                   help='missing ID of user review the artifact')
        self.reqparse.add_argument(name='reviewid',
                                   type=int,
                                   required=False,
                                   help='missing review ID')
        self.reqparse.add_argument(name='subject',
                                   type=str,
                                   required=False,
                                   help='missing subject for review of artifact')
        self.reqparse.add_argument(name='review',
                                   type=str,
                                   required=False,
                                   help='missing review for artifact')

    def post(self, artifact_id):
        args = self.reqparse.parse_args()
        api_key = args['api_key']
        if config_name == 'production':
            sso_token = args['token']
        user_id = args['userid']
        subject = args['subject']
        review = args['review']

        # verify session credentials
        verify_api_key(api_key)
        if config_name == 'production' and not verify_token(sso_token):
            abort(401, "no active login session found. please login to continue")

        # check for valid artifact id
        artifact = db.session.query(Artifact).filter(
            Artifact.id == artifact_id).first()
        if not artifact:
            abort(400, description='invalid artifact ID')

        # check if there exists a review by same user for same artifact already
        existing_review = db.session.query(ArtifactReviews).filter(ArtifactReviews.artifact_id == artifact_id, ArtifactReviews.user_id == user_id).first()

        # if it does, update the review, else add a new review
        if existing_review:
            existing_review.review = review
            existing_review.subject = subject
            existing_review.review_time = datetime.now()
            message = "updated existing review"
        else:
            new_review = ArtifactReviews(
                user_id=user_id, artifact_id=artifact_id, review=review, review_time=datetime.now(), subject=subject)
            db.session.add(new_review)
            message = "added new review"
        db.session.commit()

        response = jsonify({"message": message})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

    def put(self, artifact_id):
        args = self.reqparse.parse_args()
        api_key = args['api_key']
        if config_name == 'production':
            sso_token = args['token']
        user_id = args['userid']
        review_id = args['reviewid']
        review = args['review']
        subject = args['subject']

        # verify session credentials
        verify_api_key(api_key)
        if config_name == 'production' and not verify_token(sso_token):
            abort(401, "no active login session found. please login to continue")

        existing_review = db.session.query(ArtifactReviews).filter(
            ArtifactReviews.id == review_id, ArtifactReviews.user_id == user_id, ArtifactReviews.artifact_id == artifact_id).first()
        existing_review.review = review
        existing_review.subject = subject
        db.session.commit()

        response = jsonify({"message": "updated review"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

    def delete(self, artifact_id):
        args = self.reqparse.parse_args()
        api_key = args['api_key']
        if config_name == 'production':
            sso_token = args['token']
        user_id = args['userid']
        review_id = args['reviewid']

        # verify session credentials
        verify_api_key(api_key)
        if config_name == 'production' and not verify_token(sso_token):
            abort(401, "no active login session found. please login to continue")

        existing_review = db.session.query(ArtifactReviews).filter(
            ArtifactReviews.id == review_id, ArtifactReviews.user_id == user_id, ArtifactReviews.artifact_id == artifact_id).first()
        if existing_review:
            db.session.delete(existing_review)
            db.session.commit()
            response = jsonify({"message": "deleted review"})
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.status_code = 200
            return response
        else:
            abort(404, description="invalid review ID")
