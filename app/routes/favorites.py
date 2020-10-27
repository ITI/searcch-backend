from app import db
from app.models.model import *
from app.models.schema import *
from flask import request, jsonify, render_template, Blueprint
import json
import pprint

favorites_bp = Blueprint('favorites', __name__, url_prefix='favorites')

@favorites_bp.route("/", methods=['POST'])
def add_new_favorite():
    args = request.get_json()
    
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
