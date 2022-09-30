# logic for /artifacts

from searcch_backend.api.app import db
from searcch_backend.models.model import *
from searcch_backend.models.schema import *
from searcch_backend.api.common.stats import StatsResource
from flask import abort, jsonify, url_for, request
from flask_restful import reqparse, Resource
from sqlalchemy import func, desc, sql, or_, and_, exc
from searcch_backend.api.common.auth import (verify_api_key, has_api_key, has_token, verify_token)
import math
import logging
import json
from sqlalchemy.dialects import postgresql

LOG = logging.getLogger(__name__)

class ArtifactRequestAPI(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        super(ArtifactRequestAPI, self).__init__()

    def get(self, artifact_group_id, artifact_id=None):
        if has_api_key(request):
            verify_api_key(request)

        # Verify the group exists
        artifact_group = db.session.query(ArtifactGroup).filter(
            ArtifactGroup.id == artifact_group_id).first()
        if not artifact_group:
            abort(404, description="nonexistent artifact group")

        #
        # Determine which artifact record to return.
        #
        # If the artifact_id is not specified, there must be a publication
        # record for the group, unless: 1) caller is owner and has a draft; 2)
        # caller is admin and gets the most recent draft.  I do not like this
        # because it might be confusing, but we have to do it because a user
        # can add a relationship to an unpublished artifact (and
        # favorite/review/rate it), and we don't want to break the frontend for
        # the user or admins.
        #
        # If the artifact_id is specified, and if it is published, anyone can
        # retrieve it.  If not published, only the owner of the group or of the
        # artifact, or an admin, may retrieve it.
        #
        artifact = None
        if not artifact_id:
            if not artifact_group.publication:
                login_session = None
                if has_token(request):
                    login_session = verify_token(request)
                if not (login_session
                        and (login_session.user_id == artifact_group.owner_id
                             or login_session.is_admin)):
                    abort(400, description="insufficient permission to access unpublished artifact")
                # Find the most recent owner draft
                artifact = db.session.query(Artifact)\
                  .filter(Artifact.artifact_group_id == artifact_group_id)\
                  .filter(Artifact.owner_id == artifact_group.owner_id)\
                  .order_by(desc(Artifact.ctime))\
                  .first()
            else:
                artifact = artifact_group.publication.artifact
        else:
            res = db.session.query(Artifact, ArtifactPublication)\
              .join(ArtifactPublication, ArtifactPublication.artifact_id == Artifact.id, isouter=True)\
              .filter(and_(Artifact.id == artifact_id,Artifact.artifact_group_id == artifact_group_id))\
              .first()
            if not res:
                abort(404, description="no such artifact")
            (artifact, publication) = res
            if not artifact:
                abort(404, description="no such artifact")
            if not publication:
                login_session = None
                if has_token(request):
                    login_session = verify_token(request)
                if not (login_session
                        and (login_session.user_id == artifact_group.owner_id
                             or login_session.user_id == artifact.owner_id
                             or login_session.is_admin)):
                    abort(400, description="insufficient permission to access artifact")

        # get average rating for the artifact, number of ratings
        rating_aggregates = db.session.query(ArtifactRatings.artifact_group_id, func.count(ArtifactRatings.id).label('num_ratings'), func.avg(
            ArtifactRatings.rating).label('avg_rating')).filter(ArtifactRatings.artifact_group_id == artifact_group.id).group_by("artifact_group_id").all()

        ratings = db.session.query(ArtifactRatings, ArtifactReviews).join(ArtifactReviews, and_(
            ArtifactRatings.user_id == ArtifactReviews.user_id,
            ArtifactRatings.artifact_group_id == ArtifactReviews.artifact_group_id
        )).filter(ArtifactRatings.artifact_group_id == artifact_group.id).all()

        # Record Artifact view in database
        # XXX: need to handle API-only case.
        session_id = request.cookies.get('session_id')
        if session_id:
            stat_view_obj = StatsResource(artifact_group_id=artifact_group_id, session_id=session_id)
            stat_view_obj.recordView()

        response = jsonify({
            "artifact": ArtifactSchema().dump(artifact),
            "avg_rating": float(rating_aggregates[0][2]) if rating_aggregates else None,
            "num_ratings": rating_aggregates[0][1] if rating_aggregates else 0,
            "num_reviews": len(ratings) if ratings else 0,
            "rating_review": [{
                "rating": ArtifactRatingsSchema(only=("rating",)).dump(rating), 
                "review": ArtifactReviewsSchema(exclude=("artifact_group_id", "user_id")).dump(review)
                } for rating, review in ratings]
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

