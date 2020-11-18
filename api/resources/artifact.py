# logic for /artifacts

from api.app import db
from models.model import *
from models.schema import *
from flask import abort, jsonify, request, make_response, Blueprint, url_for
from flask_restful import reqparse, Resource, fields, marshal
from sqlalchemy import func, desc, sql


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
                sql.expression.bindparam("zero",0).label("rank"),
                'num_ratings',
                'avg_rating',
                'num_reviews'
                ).join(sqratings, Artifact.id == sqratings.c.artifact_id, isouter=True
                ).join(sqreviews, Artifact.id == sqreviews.c.artifact_id, isouter=True
                ).order_by(desc(Artifact.id)
                ).paginate(max_per_page=20).items
        else:
            res = db.session.query(Artifact,
                        func.ts_rank_cd(Artifact.document_with_idx, func.plainto_tsquery("english", keywords)).label("rank"),
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


class ArtifactAPI(Resource):
    def get(self, artifact_id):
        artifact = db.session.query(Artifact).filter(
            Artifact.id == artifact_id).first()
        if not artifact:
            abort(404, description='invalid ID for artifact')

        # get average rating for the artifact, number of ratings
        sqratings = db.session.query(ArtifactRatings.artifact_id, func.count(ArtifactRatings.id).label('num_ratings'), func.avg(
            ArtifactRatings.rating).label('avg_rating')).filter(ArtifactRatings.artifact_id == artifact_id).group_by("artifact_id").all()
        sqreviews = db.session.query(ArtifactReviews).filter(
            ArtifactReviews.artifact_id == artifact_id).all()

        artifact_affiliations = db.session.query(ArtifactAffiliation.affiliation_id).filter(
            ArtifactAffiliation.artifact_id == artifact_id).subquery()
        affiliations = db.session.query(Affiliation).filter(
            Affiliation.id.in_(artifact_affiliations)).all()

        artifact_schema = ArtifactSchema()
        affiliation_schema = AffiliationSchema(many=True)

        review_schema = ArtifactReviewsSchema(many=True)

        response = jsonify({
            "artifact": artifact_schema.dump(artifact),
            "affiliations": affiliation_schema.dump(affiliations),
            "num_ratings": sqratings[0][1] if sqratings else 0,
            "avg_rating": float(sqratings[0][2]) if sqratings else None,
            "num_reviews": len(sqreviews) if sqreviews else 0,
            "reviews": review_schema.dump(sqreviews)
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response
