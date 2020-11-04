from app import db
from app.models.model import *
from app.models.schema import *
from flask import request, jsonify, render_template, Blueprint
import json
import pprint
from sqlalchemy.sql.expression import func

# artifacts_bp = Blueprint('artifacts', __name__, url_prefix='/artifacts')
artifacts_bp = Blueprint('artifacts', __name__)


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

        # docs = db.session.query(Artifact,
        #                         func.ts_rank(Artifact.document_with_idx,
        #                                      Artifact.document_with_idx.match(kwrds, postgresql_regconfig='english'))
        #                         .label('rank'))\
        #     .filter(Artifact.document_with_idx.match(kwrds, postgresql_regconfig='english'))\
        #     .all()
        # rank = func.ts_rank('{0.1,0.1,0.1,0.1}', Artifact.document_with_idx, func.to_tsquery('english', kwrds)).label('rank')
        
        # docs = db.session.query(Artifact).filter(Artifact.document_with_idx.match(
        #     kwrds, postgresql_regconfig='english')).order_by(
        #         func.ts_rank(Artifact.document_with_idx, Artifact.document_with_idx.match(kwrds, postgresql_regconfig='english'))
        #     ).limit(1)

    artifacts = []
    for doc in docs:
        print(doc)
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

    # get artifact info
    artifact = db.session.query(Artifact).filter(
        Artifact.id == artifact_id).first()

    if artifact:
        # get all affiliations with users
        artifact_affiliations = db.session.query(ArtifactAffiliation.affiliation_id)\
            .filter(ArtifactAffiliation.artifact_id == artifact_id)\
            .subquery()
        affiliations = db.session.query(Affiliation)\
            .filter(Affiliation.id.in_(artifact_affiliations))\
            .all()

        artifact_schema = ArtifactSchema()
        affiliation_schema = AffiliationSchema(many=True)

        result = {"artifact": artifact_schema.dump(
            artifact), "affiliations": affiliation_schema.dump(affiliations)}
        response = jsonify(result)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200
    else:
        return "No document found!", 404
