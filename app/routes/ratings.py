from app import db
from app.models.model import *
from app.models.schema import *
from flask import request, jsonify, render_template, Blueprint
import json
import pprint

ratings_bp = Blueprint('artifact_ratings', __name__, url_prefix='ratings')


@ratings_bp.route('/<int:artifact_id>', methods=['GET'])
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
    ratings = db.session.query(ArtifactRatings).filter(
        ArtifactRatings.artifact_id == artifact_id).first()

    if ratings:
        artifact_ratings_schema = ArtifactRatingsSchema()

        result = {
            "ratings": artifact_ratings_schema.dump(ratings)
            }
        response = jsonify(result)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200
    else:
        return "No document found!", 404
