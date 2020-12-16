# logic for /artifacts

from searcch_backend.api.app import db
from searcch_backend.api.common.sql import object_from_json
from searcch_backend.api.common.auth import verify_api_key
from searcch_backend.models.model import *
from searcch_backend.models.schema import *
from flask import abort, jsonify, request, make_response, Blueprint, url_for, Response
from flask_restful import reqparse, Resource, fields, marshal
import sqlalchemy
from sqlalchemy import func, desc, sql, and_


class ArtifactListAPI(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        """
        possible filters:
            - keywords
            - author
            - type
            - organization
        """
        self.reqparse.add_argument(name='keywords',
                                   type=str,
                                   required=False,
                                   help='missing keywords in query string')
        self.reqparse.add_argument(name='api_key',
                                   type=str,
                                   required=False,
                                   default='')
        # TODO: add all filters for filtered search here

        super(ArtifactListAPI, self).__init__()

    @staticmethod
    def generate_artifact_uri(artifact_id):
        return url_for('api.artifact', artifact_id=artifact_id)

    def get(self):
        args = self.reqparse.parse_args()
        keywords = args['keywords']

        sqratings = db.session.query(
            ArtifactRatings.artifact_id,
            func.count(ArtifactRatings.id).label('num_ratings'),
            func.avg(ArtifactRatings.rating).label('avg_rating')
        ).group_by("artifact_id").subquery()
        sqreviews = db.session.query(
            ArtifactReviews.artifact_id,
            func.count(ArtifactReviews.id).label('num_reviews')
        ).group_by("artifact_id").subquery()
        if not keywords:
            res = db.session.query(
                Artifact,
                sql.expression.bindparam("zero", 0).label("rank"),
                'num_ratings',
                'avg_rating',
                'num_reviews'
            ).join(sqratings, Artifact.id == sqratings.c.artifact_id, isouter=True
                   ).join(sqreviews, Artifact.id == sqreviews.c.artifact_id, isouter=True
                          ).order_by(desc(Artifact.id)
                                     ).paginate(max_per_page=20).items
        else:
            res = db.session.query(Artifact,
                                   func.ts_rank_cd(Artifact.document_with_idx, func.plainto_tsquery(
                                       "english", keywords)).label("rank"),
                                   'num_ratings',
                                   'avg_rating',
                                   'num_reviews'
                                   ).filter(Artifact.document_with_idx.op('@@')(func.plainto_tsquery("english", keywords))
                                            ).join(sqratings, Artifact.id == sqratings.c.artifact_id, isouter=True
                                                   ).join(sqreviews, Artifact.id == sqreviews.c.artifact_id, isouter=True
                                                          ).order_by(desc("rank")
                                                                     ).all()

        artifacts = []
        for artifact, relevance_score, num_ratings, avg_rating, num_reviews in res:
            result = {
                "id": artifact.id,
                "uri": ArtifactListAPI.generate_artifact_uri(artifact.id),
                "doi": artifact.url,
                "type": artifact.type,
                "relevance_score": relevance_score,
                "title": artifact.title,
                "description": artifact.description,
                "avg_rating": float(avg_rating) if avg_rating else None,
                "num_ratings": num_ratings if num_ratings else 0,
                "num_reviews": num_reviews if num_reviews else 0
            }
            artifacts.append(result)

        response = jsonify({"artifacts": artifacts, "length": len(artifacts)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

    def post(self):
        """
        Creates a new artifact from the given JSON document, without invoking the importer.
        """
        args = self.reqparse.parse_args()
        api_key = args['api_key']
        verify_api_key(api_key)
        j = request.json
        del j["api_key"]
        artifact = object_from_json(db.session, Artifact, j, skip_ids=None)
        db.session.add(artifact)
        try:
            db.session.commit()
        except sqlalchemy.exc.IntegrityError:
            # psycopg2.errors.UniqueViolation:
            abort(400, description="duplicate artifact")
        except:
            abort(500)
        db.session.expire_all()
        response = jsonify({"id": artifact.id})
        response.status_code = 200
        return response


class ArtifactAPI(Resource):
    def get(self, artifact_id):
        artifact = db.session.query(Artifact).filter(
            Artifact.id == artifact_id).first()
        if not artifact:
            abort(404, description='invalid ID for artifact')

        # get average rating for the artifact, number of ratings
        rating_aggregates = db.session.query(ArtifactRatings.artifact_id, func.count(ArtifactRatings.id).label('num_ratings'), func.avg(
            ArtifactRatings.rating).label('avg_rating')).filter(ArtifactRatings.artifact_id == artifact_id).group_by("artifact_id").all()

        ratings = db.session.query(ArtifactRatings, ArtifactReviews).join(ArtifactReviews, and_(
            ArtifactRatings.user_id == ArtifactReviews.user_id,
            ArtifactRatings.artifact_id == ArtifactReviews.artifact_id
        )).filter(ArtifactRatings.artifact_id == artifact_id).all()
        print(ratings)

        # res = ReviewRatingNestedSchema(many=True).dump(ratings)

        response = jsonify({
            "artifact": ArtifactSchema().dump(artifact),
            "avg_rating": float(rating_aggregates[0][2]) if rating_aggregates else None,
            "num_ratings": rating_aggregates[0][1] if rating_aggregates else 0,
            "num_reviews": len(ratings) if ratings else 0,
            "rating_review": [{
                "rating": ArtifactRatingsSchema(only=("rating",)).dump(rating), 
                "review": ArtifactReviewsSchema(exclude=("id", "artifact_id", "user_id")).dump(review)
                } for rating, review in ratings]
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response
