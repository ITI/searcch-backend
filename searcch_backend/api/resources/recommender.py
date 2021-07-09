from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.auth import (verify_api_key, verify_token)
from searcch_backend.models.model import *
from searcch_backend.models.schema import *
from flask import abort, jsonify, request, make_response, Blueprint
from flask_restful import reqparse, Resource, fields, marshal
import json


class KeywordsAPI(Resource):
    def get(self, artifact_id):
        verify_api_key(request)
        login_session = verify_token(request)

        # check for valid artifact id
        artifact = db.session.query(Artifact).filter(
            Artifact.id == artifact_id).first()
        if not artifact:
            abort(400, description='invalid artifact ID')

        top_keywords = db.session.query(ArtifactMetadata.value).filter(
            ArtifactMetadata.artifact_id == artifact_id, ArtifactMetadata.name == "top_ngram_keywords").first()
        if not top_keywords:
            response = jsonify(
                {"message": "The artifact doesnt have any top rated keywords"})
        else:
            top_keywords_list = json.loads(top_keywords[0])
            keywords = []
            for keyword in top_keywords_list:
                keywords.append(keyword[0])
            response = jsonify({"artifact_id": artifact_id,"keywords": keywords})



        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response