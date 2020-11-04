from app import db
from app.models.model import *
from app.models.schema import *
from flask import request, jsonify, render_template, Blueprint
import json
import pprint
from sqlalchemy.sql import func

ratings_bp = Blueprint('ratings', __name__, url_prefix='ratings')


@ratings_bp.route('/<int:artifact_id>', methods=['GET'])
def get_average_rating_by_artifact_id(artifact_id):
    # TODO: verify API key
    # TODO: verify session token
    
    # get average rating by artifact id
    average_rating = func.avg(ArtifactRatings.rating).label('average_rating')
    ratings = db.session.query(average_rating).filter(ArtifactRatings.artifact_id == artifact_id)

    if ratings:
        result = {
            "artifact_id": artifact_id,
            "rating": ratings[0].average_rating
        }
        response = jsonify(result)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200
    else:
        return "No document found!", 404

@ratings_bp.route('/', methods=['POST'])
def create_new_rating():
    # TODO: verify API key
    # TODO: verify session token

    user_id = request.args.get('user_id')
    artifact_id = request.args.get('artifact_id')
    rating = request.args.get('rating')
    new_rating = ArtifactRatings(user_id=user_id, artifact_id=artifact_id,rating=rating)
    db.session.add(new_rating)
    db.session.commit()

    response = jsonify({"message": "added new rating"})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response, 200