from app import db
from app.models.model import *
from app.models.schema import *
from app.models.encoder import alchemy_encoder
from flask import request, jsonify, render_template, Blueprint
import json
import pprint

artifacts_bp = Blueprint('artifacts', __name__, url_prefix='artifacts')


@artifacts_bp.route("/", methods=['GET'])
def search_with_keywords():
    """
    searches for artifacts matching supplied keywords

    Returns
    -------
    JSON
        {
            "length": <# of ARTIFACTS>,
            "artifacts": [ { <ARTIFACT DATA> } ]
        }
    """
    # return "reached endpoint"
    if "keywords" not in request.args:
        return 'keyword(s) are missing!', 400

    kwrds = request.args.get('keywords')
    if kwrds == "":
        docs = db.session.query(Artifact).limit(20).all()
    else:
        docs = db.session.query(Artifact).filter(Artifact.document_with_idx.match(
            kwrds, postgresql_regconfig='english')).all()

    artifacts = []
    for doc in docs:
        result = {
            "url": doc.url,
            "title": doc.title,
            "description": doc.description,
            "type": doc.type,
            "id": doc.id
            # TODO: write join query to get relevance score
        }
        artifacts.append(result)

    response = jsonify({"artifacts": artifacts, "length": len(artifacts)})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response, 200


@artifacts_bp.route('/<int:artifact_id>', methods=['GET'])
def get_artifact_by_id(artifact_id):
    """
    gets all data for artifact with supplied id

    Parameters
    ----------
    artifact_id : Integer
        unique identifier for each artifact

    Returns
    -------
    JSON
        artifact information and metadata
    """

    # get artifact with id 1
    # artifact = db.session.query(Artifact).get(artifact_id)
    artifact = db.session.query(Artifact).join(ArtifactTag).filter(Artifact.id == artifact_id).all()
    print(artifact)
    # metadata = db.session.query(ArtifactMetadata).filter_by(artifact_id=artifact_id)
    # tags = db.session.query(ArtifactTag).filter_by(artifact_id=artifact_id)
    # files = db.session.query(ArtifactFile).filter_by(artifact_id=artifact_id)
    # owner = db.session.query(Person).get(artifact.owner_id)

    artifact_schema = ArtifactSchema()
    print(artifact_schema.dump(artifact))

    if artifact:
        response = jsonify(artifact_schema.dump(artifact))
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200
    else:
        return "No document found!", 404
