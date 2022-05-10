import logging
import sys
import json

from flask import abort, jsonify, request
from flask_restful import reqparse, Resource

from searcch_backend.models.model import (
    ArtifactGroup, Artifact)
from searcch_backend.models.schema import (
    ArtifactSchema, ArtifactCurationSchema )
from searcch_backend.api.app import db
from searcch_backend.api.common.auth import (verify_api_key, verify_token, has_token)
from searcch_backend.api.common.sql import artifact_diff_by_value

LOG = logging.getLogger(__name__)

class ArtifactCompareAPI(Resource):

    def __init__(self):
        self.getparse = reqparse.RequestParser()
        self.getparse.add_argument(
            name="target_artifact_id", type=int, required=True, location="args",
            help="Must supply a target artifact_id, in the same artifact_group as the path artifact.")

        super(ArtifactCompareAPI, self).__init__()

    def get(self, artifact_group_id, artifact_id):
        """
        Get a list of curations (differences) between two artifacts.
        """
        verify_api_key(request)
        if has_token(request):
            login_session = verify_token(request)

        args = self.getparse.parse_args()
        target_artifact_id = args.target = args["target_artifact_id"]

        artifact = db.session.query(Artifact)\
          .filter(Artifact.id == artifact_id)\
          .filter(Artifact.artifact_group_id == artifact_group_id)\
          .first()
        if not artifact:
            abort(404, description="no such artifact")
        if not artifact.publication:
            if not login_session:
                abort(401)
            if not (login_session.user_id == artifact.owner_id
                    or login_session.is_admin):
                abort(403, description="not authorized to access artifact")

        target_artifact = db.session.query(Artifact)\
          .filter(Artifact.id == target_artifact_id)\
          .first()
        if not target_artifact:
            abort(404, description="no such target artifact")
        if not target_artifact.publication:
            if not login_session:
                abort(401)
            if not (login_session.user_id == target_artifact.owner_id
                    or login_session.is_admin):
                abort(403, description="not authorized to access target artifact")

        if artifact.artifact_group_id != target_artifact.artifact_group_id:
            abort(400, description="artifact and target_artifact are in different artifact groups")

        curations = artifact_diff_by_value(
            db.session, None, artifact, artifact, target_artifact,
            update=False)

        response_dict = dict(
            curations=ArtifactCurationSchema(many=True).dump(curations),
            artifact=ArtifactSchema().dump(artifact),
            target_artifact=ArtifactSchema().dump(target_artifact)
        )
        response = jsonify(response_dict)
        response.status_code = 200
        return response
