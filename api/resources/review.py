# logic for /review

from api.app import db
from api.common.auth import *
from models.model import *
from models.schema import *
from datetime import datetime
from flask import abort, jsonify, request, make_response, Blueprint
from flask_restful import reqparse, Resource, fields, marshal


class ReviewAPI(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument(name='token',
                                   type=str,
                                   required=False,
                                   default='',
                                   location='form',
                                   help='missing SSO token from auth provider in post request')
        self.reqparse.add_argument(name='api_key',
                                   type=str,
                                   required=False,
                                   default='',
                                   location='form',
                                   help='missing API secret key in post request')
        self.reqparse.add_argument(name='reviewid',
                                   type=int,
                                   required=False,
                                   location='form',
                                   help='missing review ID')
        self.reqparse.add_argument(name='userid',
                                   type=int,
                                   required=False,
                                   location='form',
                                   help='missing ID of user rating the artifact')
        self.reqparse.add_argument(name='subject',
                                   type=str,
                                   required=False,
                                   location='form',
                                   help='missing subject for review of artifact')
        self.reqparse.add_argument(name='review',
                                   type=str,
                                   required=False,
                                   location='form',
                                   help='missing review for artifact')

    def get(self, artifact_id):
        args = self.reqparse.parse_args()
        user_id = args['userid']

        # check for valid artifact id
        artifact = db.session.query(Artifact).filter(
            Artifact.id == artifact_id).first()
        if not artifact:
            abort(400, description='invalid artifact ID')

        # TODO: get username for review user
        reviews = db.session.query(ArtifactReviews).filter(ArtifactReviews.artifact_id == artifact_id).all()
        review_schema = ArtifactReviewsSchema(many=True)
        if not reviews:
            response = jsonify(
                {"reviews": []})
        else:
            response = jsonify({"reviews": review_schema.dump(reviews)})

        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response
    

    def post(self, artifact_id):
        args = self.reqparse.parse_args()
        api_key = args['api_key']
        sso_token = args['token']
        user_id = args['userid']
        subject = args['subject']
        review = args['review']

        # verify session credentials
        verify_api_key(api_key)
        if not verify_token(sso_token):
            abort(401, "no active login session found. please login to continue")

        # check for valid artifact id
        artifact = db.session.query(Artifact).filter(
            Artifact.id == artifact_id).first()
        if not artifact:
            abort(400, description='invalid artifact ID')

        # add new review to the database
        new_review = ArtifactReviews(
            user_id=user_id, artifact_id=artifact_id, review=review, review_time=datetime.now(), subject=subject)
        db.session.add(new_review)
        db.session.commit()

        response = jsonify({"message": "added new review"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

    def put(self, artifact_id):
        args = self.reqparse.parse_args()
        api_key = args['api_key']
        sso_token = args['token']
        user_id = args['userid']
        review_id = args['reviewid']
        review = args['review']

        # verify session credentials
        verify_api_key(api_key)
        if not verify_token(sso_token):
            abort(401, "no active login session found. please login to continue")

        existing_review = db.session.query(ArtifactReviews).filter(
            ArtifactReviews.id == review_id, ArtifactReviews.user_id == user_id, ArtifactReviews.artifact_id == artifact_id).first()
        existing_review.review = review
        db.session.commit()

        response = jsonify({"message": "updated review"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response
    
    def delete(self, artifact_id):
        args = self.reqparse.parse_args()
        api_key = args['api_key']
        sso_token = args['token']
        user_id = args['userid']
        review_id = args['reviewid']

        # verify session credentials
        verify_api_key(api_key)
        if not verify_token(sso_token):
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
