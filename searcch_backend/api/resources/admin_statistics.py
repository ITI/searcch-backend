# logic for /rating

from searcch_backend.api.app import db, config_name, mail
from searcch_backend.api.common.auth import (verify_api_key, has_api_key)
from searcch_backend.api.common.sql import object_from_json
from searcch_backend.models.model import *
from searcch_backend.models.schema import *
from flask import abort, jsonify, request
from flask_restful import reqparse, Resource, fields, marshal
from sqlalchemy import func, desc, asc, sql, or_
import sys
import logging
import math


from random import * 

LOG = logging.getLogger(__name__)
class AdminStatistics(Resource):

    def __init__(self):
        super(AdminStatistics, self).__init__()

    def get(self):
        if has_api_key(request):
            verify_api_key(request)

        # args = self.getparse.parse_args()
        num_requests = db.session.query(func.count()).select_from(ArtifactRequests).scalar()
        num_ratings = db.session.query(func.count()).select_from(ArtifactRatings).scalar()
        num_reviews = db.session.query(func.count()).select_from(ArtifactReviews).scalar()
        category_count_results = db.session.query(Artifact.category, func.count(Artifact.category)).group_by(Artifact.category).all()
        category_count = {}
        for category, count in category_count_results:
            category_count[category] = count

        provider_count_results = db.session.query(Artifact.provider, func.count(Artifact.provider)).group_by(Artifact.provider).all()
        provider_count = {}
        for provider, count in provider_count_results:
            provider_count[provider] = count

        response_dict = {
            "num_requests": num_requests,
            "num_reviews": num_reviews,
            "num_ratings": num_ratings,
            "category_count" : category_count,
            "provider_count" : provider_count,
        }
        response = jsonify(response_dict)

        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response


