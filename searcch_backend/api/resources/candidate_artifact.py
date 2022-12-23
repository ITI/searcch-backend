import logging

from flask import abort, jsonify, request, Response
from flask_restful import reqparse, Resource

from searcch_backend.models.model import (
    CandidateArtifact )
from searcch_backend.api.app import db
from searcch_backend.api.common.auth import (verify_api_key, verify_token)

LOG = logging.getLogger(__name__)

class CandidateArtifactResource(Resource):

    def delete(self, candidate_artifact_id):
        """
        Deletes a candidate artifact if the candidate artifact has not yet been imported, as well as any candidate artifact relationships that reference it.
        """
        verify_api_key(request)
        login_session = verify_token(request)

        candidate_artifact = db.session.query(CandidateArtifact).\
          filter(CandidateArtifact.id == candidate_artifact_id).\
          filter(CandidateArtifact.owner_id == login_session.user_id).\
          first()
        if not candidate_artifact:
            abort(404, description="invalid candidate artifact ID")
        if candidate_artifact.owner_id != login_session.user_id:
            abort(403, description="insufficient permission to modify candidate artifact")
        if candidate_artifact.artifact_import_id:
            abort(400, description="already imported this artifact; cannot delete")

        for car in candidate_artifact.candidate_artifact_relationships:
            db.session.delete(car)
        candidate_artifact.candidate_artifact_relationships = []
        db.session.delete(candidate_artifact)
        db.session.commit()
        return Response(status=200)
