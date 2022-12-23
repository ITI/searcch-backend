
from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.auth import verify_api_key
from flask import abort, jsonify, request
from flask_restful import reqparse, Resource
import sqlalchemy
from sqlalchemy import func, asc, desc, sql, and_, or_
import logging
from searcch_backend.models.model import *
from searcch_backend.models.schema import *

LOG = logging.getLogger(__name__)

class DUAResource(Resource):

    def __init__(self):
        super(DUAResource, self).__init__()

    def get(self, artifact_group_id):
        dua_name = db.session.query(DUA.dua_url).join(Artifact, Artifact.provider == DUA.provider).filter(artifact_group_id == Artifact.artifact_group_id).first()[0]
        dua_file = open(f'searcch_backend/api/dua_content/{dua_name}', mode='r')
        dua_content = dua_file.read()
        dua_file.close()
        response = jsonify({"dua": dua_content})
        response.status_code = 200
        return response
