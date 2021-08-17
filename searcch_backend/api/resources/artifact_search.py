# logic for /artifacts

from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.sql import (object_from_json, artifact_diff)
from searcch_backend.api.common.auth import (verify_api_key, has_api_key, has_token, verify_token)
from searcch_backend.models.model import *
from searcch_backend.models.schema import *
from flask import abort, jsonify, request, make_response, Blueprint, url_for, Response
from flask_restful import reqparse, Resource, fields, marshal
import sqlalchemy
from sqlalchemy import func, desc, sql, and_, or_
import datetime
import json
import sys
import logging

LOG = logging.getLogger(__name__)

def generate_artifact_uri(artifact_id):
    return url_for('api.artifact', artifact_id=artifact_id)

def search_artifacts( keywords, artifact_types, page_num):
    """ search for artifacts based on keywords """
    sqratings = db.session.query(
        ArtifactRatings.artifact_id,
        func.count(ArtifactRatings.id).label('num_ratings'),
        func.avg(ArtifactRatings.rating).label('avg_rating')
    ).group_by("artifact_id").subquery()
    sqreviews = db.session.query(
        ArtifactReviews.artifact_id,
        func.count(ArtifactReviews.id).label('num_reviews')
    ).group_by("artifact_id").subquery()

    # create base query object
    if not keywords:
        query = db.session.query(Artifact,
                                    sql.expression.bindparam("zero", 0).label("rank"),
                                    'num_ratings', 'avg_rating', 'num_reviews'
                                    ).order_by(
                                    db.case([
                                        (Artifact.type == 'software', 1),
                                        (Artifact.type == 'dataset', 2),
                                        (Artifact.type ==
                                        'publication', 3),
                                    ], else_=4)
                                )      
        query = query.join(sqratings, Artifact.id == sqratings.c.artifact_id, isouter=True
                        ).join(sqreviews, Artifact.id == sqreviews.c.artifact_id, isouter=True
                        ).order_by(sqratings.c.avg_rating.desc().nullslast(),sqreviews.c.num_reviews.desc())
    else:
        search_query = db.session.query(ArtifactSearchMaterializedView.artifact_id, 
                                        func.ts_rank_cd(ArtifactSearchMaterializedView.doc_vector, func.websearch_to_tsquery("english", keywords)).label("rank")
                                    ).filter(ArtifactSearchMaterializedView.doc_vector.op('@@')(func.websearch_to_tsquery("english", keywords))
                                    ).subquery()
        query = db.session.query(Artifact, 
                                    search_query.c.rank, 'num_ratings', 'avg_rating', 'num_reviews'
                                    ).join(search_query, Artifact.id == search_query.c.artifact_id, isouter=False)
        
        query = query.join(sqratings, Artifact.id == sqratings.c.artifact_id, isouter=True
                        ).join(sqreviews, Artifact.id == sqreviews.c.artifact_id, isouter=True
                        ).order_by(desc(search_query.c.rank))

    # add filters based on provided parameters
    if artifact_types:
        if len(artifact_types) > 1:
            query = query.filter(or_(Artifact.type == a_type for a_type in artifact_types))
        else:
            query = query.filter(Artifact.type == artifact_types[0])

    
    result = query.paginate(page=page_num, error_out=False, max_per_page=20).items

    artifacts = []
    for row in result:
        artifact, relevance_score, num_ratings, avg_rating, num_reviews = row
        if artifact.publication:  # return only published artifacts
            abstract = {
                "id": artifact.id,
                "uri": generate_artifact_uri(artifact.id),
                "doi": artifact.url,
                "type": artifact.type,
                "title": artifact.title,
                "description": artifact.description,
                "avg_rating": float(avg_rating) if avg_rating else None,
                "num_ratings": num_ratings if num_ratings else 0,
                "num_reviews": num_reviews if num_reviews else 0,
                "owner": { "id": artifact.owner.id }
            }
            artifacts.append(abstract)
    return artifacts

class ArtifactSearchIndexAPI(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument(name='keywords',
                                   type=str,
                                   required=False,
                                   help='missing keywords in query string')
        self.reqparse.add_argument(name='page',
                                   type=int,
                                   required=False,
                                   default=1,
                                   help='page number for paginated results')
        self.reqparse.add_argument(name='items_per_page',
                                   type=int,
                                   required=False,
                                   default=20,
                                   help='items per page for paginated results')
        
        # filters
        self.reqparse.add_argument(name='type',
                                   type=str,
                                   required=False,
                                   action='append',
                                   help='missing type to filter results')
        self.reqparse.add_argument(name='entity',
                                   type=str,
                                   required=False,
                                   action='append',
                                   help='missing entities to search for')

        super(ArtifactSearchIndexAPI, self).__init__()


    @staticmethod
    def is_artifact_type_valid(artifact_type):
        return artifact_type in ARTIFACT_TYPES

    def search_users(self, keywords, page_num):
        """ search for users based on keywords """
        user_query = db.session.query(Person, func.ts_rank_cd(Person.person_tsv, func.websearch_to_tsquery("english", keywords)).label(
            "rank")).filter(Person.person_tsv.op('@@')(func.websearch_to_tsquery("english", keywords))).order_by(desc("rank"))
        result = user_query.paginate(page=page_num, error_out=False, max_per_page=20).items

        users = []
        for row in result:
            user, relevance_score = row
            abstract = {
                "user": PersonSchema().dump(user)
            }
            users.append(abstract)
        
        return users
    
    def search_organizations(self, keywords, page_num):
        """ search for organizations based on keywords """
        org_query = db.session.query(Organization, func.ts_rank_cd(Organization.org_tsv, func.websearch_to_tsquery("english", keywords)).label(
            "rank")).filter(Organization.org_tsv.op('@@')(func.websearch_to_tsquery("english", keywords))).order_by(desc("rank"))
        result = org_query.paginate(page=page_num, error_out=False, max_per_page=20).items

        orgs = []
        for row in result:
            org, relevance_score = row
            abstract = {
                "org": OrganizationSchema().dump(org)
            }
            orgs.append(abstract)
        
        return orgs

    def get(self):
        args = self.reqparse.parse_args()
        keywords = args['keywords']
        artifact_types = args['type']
        entities = args['entity']
        page_num = args['page']

        artifacts, users, organizations = [], [], []

        # sanity checks
        if artifact_types:
            for a_type in artifact_types:
                if not ArtifactSearchIndexAPI.is_artifact_type_valid(a_type):
                    abort(400, description='invalid artifact type passed')
        if entities:
            for entity in entities:
                if entity not in ['artifact', 'user', 'organization']:
                    abort(400, description='invalid entity passed')
            if 'artifact' in entities:
                artifacts = search_artifacts(keywords, artifact_types, page_num)
            if 'user' in entities:
                users = self.search_users(keywords, page_num)
            if 'organization' in entities:
                organizations = self.search_organizations(keywords, page_num)

        response = jsonify({
            "artifacts": artifacts, 
            "users": users, 
            "organizations": organizations
            })
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response
