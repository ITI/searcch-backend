from app.models.model import Artifact, ArtifactMetadata, ArtifactFile, ArtifactTag
from flask import request, jsonify, render_template, Blueprint
import json

artifacts_bp = Blueprint('artifacts', __name__, url_prefix='artifacts')


@artifacts_bp.route("/", methods=['GET'])
def search_with_keywords():
    """
    searches for artifacts matching supplied keywords

    Returns
    -------
    JSON
        {
            "length": <NUMBER OF RETURNED ARTIFACTS>,
            "artifacts": [{ "doi": <DOI>, "title": <TITLE>, "description": <DESCRIPTION> } ]
        }
    """
    return "reached endpoint"
    # if "keywords" not in request.args:
    #     return 'keyword(s) are missing!', 400

    # kwrds = request.args.get('keywords')
    # if kwrds == "":
    #     docs = Artifact.query().limit(20).all()
    # else:
    #     docs = Artifact.query().filter_by(Artifact.document_with_idx.match(
    #         kwrds, postgresql_regconfig='english')).all()

    # artifacts = []
    # for doc in docs:
    #     result = {
    #         "url": doc["url"],
    #         "title": doc["title"],
    #         "description": doc["description"],
    #         "type": doc["type"]
    #         # TODO: write join query to get relevance score
    #     }
    #     artifacts.append(result)

    # response = jsonify({"artifacts": artifacts, "length": len(artifacts)})
    # response.headers.add('Access-Control-Allow-Origin', '*')
    # return response, 200


# @artifacts_bp.route('/<int:artifact_id>', methods=['GET'])
# def get_artifact_by_id(artifact_id):
#     """get_artifact_by_id returns specific artifact by DOI

#     Parameters
#     ----------
#     artifact_id : Integer
#         unique identifier for each artifact

#     Returns
#     -------
#     JSON
#         artifact information and metadata
#     """

#     # get artifact with id 1
#     artifact = Artifact.query().get_or_404(artifact_id)
#     if artifact:
#         response = json.loads(json.dumps(artifact, default=json_util.default))
#         response = jsonify(response)
#         response.headers.add('Access-Control-Allow-Origin', '*')
#         return response, 200
#     else:
#         return "No document found!", 404
