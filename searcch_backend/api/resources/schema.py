
from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.sql import class_to_jsonschema
from searcch_backend.models.model import (Artifact, Affiliation)
import flask
from flask_restful import (Resource, reqparse)


class SchemaArtifactAPI(Resource):

    def __init__(self, *args, **kwargs):
        self.getparse = reqparse.RequestParser()
        self.getparse.add_argument(
            name="sort_keys", type=bool, required=False,
            default=False, help="Set to 1 to sort schema dict keys")

    def get(self):
        args = self.getparse.parse_args()

        content = flask.json.dumps(
            class_to_jsonschema(Artifact), indent=2, sort_keys=args.sort_keys)

        response = flask.make_response(content, 200)
        response.headers.add('Content-Type', 'application/json')
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response

class SchemaAffiliationAPI(Resource):

    def __init__(self, *args, **kwargs):
        self.getparse = reqparse.RequestParser()
        self.getparse.add_argument(
            name="sort_keys", type=bool, required=False,
            default=False, help="Set to 1 to sort schema dict keys")

    def get(self):
        args = self.getparse.parse_args()

        content = flask.json.dumps(
            class_to_jsonschema(Affiliation), indent=2, sort_keys=args.sort_keys)

        response = flask.make_response(content, 200)
        response.headers.add('Content-Type', 'application/json')
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response
