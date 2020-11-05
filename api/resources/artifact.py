# logic for /artifacts

from api.app import db
from models.model import *
from models.schema import *
from flask import abort, jsonify, request, make_response, Blueprint
from flask_restful import reqparse, Resource, fields, marshal


class ArtifactListAPI(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        # TODO: add all filters for filtered search here
        """
        possible filters:
            - keywords
            - author
            - type
            - organization
        """
        self.reqparse.add_argument(name='keywords',
                                   type=str,
                                   required=True,
                                   help='missing keywords in query string')
        # self.reqparse.add_argument(
        #     'author', type=str, required=False, help='missing author in query string')

        super(ArtifactListAPI, self).__init__()

    def get(self):
        args = self.reqparse.parse_args()
        keywords = args['keywords']
        # author = args['author']

        if keywords == '':
            docs = db.session.query(Artifact).limit(20).all()
        else:
            # TODO: retrieve relevance score from full-text search index
            # TODO: get average rating for each artifact
            docs = db.session.query(Artifact).filter(Artifact.document_with_idx.match(
                keywords, postgresql_regconfig='english')).all()

        artifacts = []
        for doc in docs:
            result = {
                "url": doc.url,
                "title": doc.title,
                "description": doc.description,
                "type": doc.type,
                # TODO: replace id with uri to artifact details endpoint
                "id": doc.id
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

        # TODO: get average rating for the artifact
        artifact_affiliations = db.session.query(ArtifactAffiliation.affiliation_id).filter(
            ArtifactAffiliation.artifact_id == artifact_id).subquery()
        affiliations = db.session.query(Affiliation).filter(
            Affiliation.id.in_(artifact_affiliations)).all()

        artifact_schema = ArtifactSchema()
        affiliation_schema = AffiliationSchema(many=True)

        response = jsonify({
            "artifact": artifact_schema.dump(artifact),
            "affiliations": affiliation_schema.dump(affiliations)
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response
