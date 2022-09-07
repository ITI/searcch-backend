
from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.sql import class_to_jsonschema
from searcch_backend.models.model import (Artifact, Affiliation)
from flask import (abort, jsonify)
from flask_restful import Resource


class SchemaArtifactAPI(Resource):
    def get(self):
        response = jsonify(class_to_jsonschema(Artifact))
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

class SchemaAffiliationAPI(Resource):
    def get(self):
        response = jsonify(class_to_jsonschema(Affiliation))
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response
