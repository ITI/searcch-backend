# logic for /rating

from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.auth import (verify_api_key, verify_token)
from searcch_backend.models.model import *
from searcch_backend.models.schema import *
from flask import abort, jsonify, request, url_for, Blueprint
from flask_restful import reqparse, Resource, fields, marshal
from sqlalchemy import func, desc, sql

def subquery_constructs():
    sqratings = db.session.query(
        ArtifactRatings.artifact_group_id,
        func.count(ArtifactRatings.id).label('num_ratings'),
        func.avg(ArtifactRatings.rating).label('avg_rating')
    ).group_by("artifact_group_id").subquery()

    sqreviews = db.session.query(
        ArtifactReviews.artifact_group_id,
        func.count(ArtifactReviews.id).label('num_reviews')
    ).group_by("artifact_group_id").subquery()
    
    return sqratings, sqreviews

class FavoritesListAPI(Resource):
    @staticmethod
    def generate_artifact_uri(artifact_group_id):
        return url_for('api.artifact', artifact_group_id=artifact_group_id)

    def get(self, user_id):
        verify_api_key(request)
        login_session = verify_token(request)

        if user_id != login_session.user_id:
            abort(401, description="insufficient permission to list favorites")

        sqratings, sqreviews = subquery_constructs()

        favorite_artifacts = db.session.query(ArtifactGroup, Artifact, 'num_ratings', 'avg_rating', 'num_reviews'
            ).join(ArtifactPublication, ArtifactGroup.publication_id == ArtifactPublication.id, isouter=True
            ).join(Artifact, ArtifactPublication.artifact_id == Artifact.id, isouter=True
            ).join(sqratings, ArtifactGroup.id == sqratings.c.artifact_group_id, isouter=True
            ).join(sqreviews, ArtifactGroup.id == sqreviews.c.artifact_group_id, isouter=True
            ).join(ArtifactFavorites, ArtifactGroup.id == ArtifactFavorites.artifact_group_id
            ).filter(ArtifactFavorites.user_id == login_session.user_id
            ).all()

        artifacts = []
        for artifact_group, artifact, num_ratings, avg_rating, num_reviews in favorite_artifacts:
            result = {
                "artifact_group_id": artifact_group.id,
                "uri": FavoritesListAPI.generate_artifact_uri(artifact.id),
                "doi": getattr(artifact, 'url', None),
                "type": getattr(artifact, 'type', None),
                "title": getattr(artifact, 'title', None),
                "description": getattr(artifact, 'description', None),
                "avg_rating": float(avg_rating) if avg_rating else None,
                "num_ratings": num_ratings if num_ratings else 0,
                "num_reviews": num_reviews if num_reviews else 0
            }
            artifacts.append(result)

        response = jsonify({"artifacts": artifacts, "length": len(artifacts)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response


class FavoriteAPI(Resource):

    def post(self, artifact_group_id):
        verify_api_key(request)
        login_session = verify_token(request)

        # check for valid artifact id
        artifact_group = db.session.query(ArtifactGroup).filter(
            ArtifactGroup.id == artifact_group_id).first()
        if not artifact_group:
            abort(400, description='invalid artifact group ID')

        # add new rating to the database
        new_favorite = ArtifactFavorites(
            user_id=login_session.user_id, artifact_group_id=artifact_group_id,
            artifact_id=artifact_group.publication.artifact_id)
        db.session.add(new_favorite)
        db.session.commit()

        response = jsonify({"message": "added artifact group to favorites list"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

    def delete(self, artifact_group_id):
        verify_api_key(request)
        login_session = verify_token(request)

        existing_favorite = db.session.query(ArtifactFavorites).filter(
            ArtifactFavorites.user_id == login_session.user_id, ArtifactFavorites.artifact_group_id == artifact_group_id).first()
        if existing_favorite:
            db.session.delete(existing_favorite)
            db.session.commit()
            response = jsonify(
                {"message": "deleted artifact group from favorites list"})
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.status_code = 200
            return response
        else:
            abort(
                404, description="this artifact group does not exist in the user's favorites list")
