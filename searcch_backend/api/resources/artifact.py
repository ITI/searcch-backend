# logic for /artifacts

from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.sql import object_from_json
from searcch_backend.api.common.auth import verify_api_key
from searcch_backend.models.model import *
from searcch_backend.models.schema import *
from flask import abort, jsonify, request, make_response, Blueprint, url_for, Response
from flask_restful import reqparse, Resource, fields, marshal
import sqlalchemy
from sqlalchemy import func, desc, sql, and_, or_
import traceback
import datetime
import json


class ArtifactListAPI(Resource):
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

        super(ArtifactListAPI, self).__init__()

    @staticmethod
    def generate_artifact_uri(artifact_id):
        return url_for('api.artifact', artifact_id=artifact_id)

    @staticmethod
    def is_artifact_type_valid(artifact_type):
        return artifact_type in ARTIFACT_TYPES

    def search_artifacts(self, keywords, artifact_types, page_num):
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
                                            (Artifact.type == 'code', 1),
                                            (Artifact.type == 'dataset', 2),
                                            (Artifact.type ==
                                            'publication', 3),
                                        ], else_=4)
                                    )                
        else:
            search_query = db.session.query(ArtifactSearchMaterializedView.artifact_id, 
                                            func.ts_rank_cd(ArtifactSearchMaterializedView.doc_vector, func.websearch_to_tsquery("english", keywords)).label("rank")
                                        ).filter(ArtifactSearchMaterializedView.doc_vector.op('@@')(func.websearch_to_tsquery("english", keywords))
                                        ).subquery()
            query = db.session.query(Artifact, 
                                        search_query.c.rank, 'num_ratings', 'avg_rating', 'num_reviews'
                                        ).join(search_query, Artifact.id == search_query.c.artifact_id, isouter=False)

        # add filters based on provided parameters
        if artifact_types:
            if len(artifact_types) > 1:
                query = query.filter(or_(Artifact.type == a_type for a_type in artifact_types))
            else:
                query = query.filter(Artifact.type == artifact_types[0])

        query = query.join(sqratings, Artifact.id == sqratings.c.artifact_id, isouter=True
                            ).join(sqreviews, Artifact.id == sqreviews.c.artifact_id, isouter=True
                            ).order_by(desc(search_query.c.rank))
        result = query.paginate(page=page_num, error_out=False, max_per_page=20).items

        artifacts = []
        for row in result:
            artifact, relevance_score, num_ratings, avg_rating, num_reviews = row
            if artifact.publication:  # return only published artifacts
                abstract = {
                    "id": artifact.id,
                    "uri": ArtifactListAPI.generate_artifact_uri(artifact.id),
                    "doi": artifact.url,
                    "type": artifact.type,
                    "relevance_score": relevance_score,
                    "title": artifact.title,
                    "description": artifact.description,
                    "avg_rating": float(avg_rating) if avg_rating else None,
                    "num_ratings": num_ratings if num_ratings else 0,
                    "num_reviews": num_reviews if num_reviews else 0
                }
                artifacts.append(abstract)
        return artifacts

    def search_users(self, keywords, page_num):
        """ search for users based on keywords """
        users = []
        return users
    
    def search_organizations(self, keywords, page_num):
        """ search for organizations based on keywords """
        organizations = []
        return organizations

    def get(self):
        args = self.reqparse.parse_args()
        keywords = args['keywords']
        artifact_types = args['type']
        entities = args['entity']
        page_num = args['page']

        # sanity checks
        if artifact_types:
            for a_type in artifact_types:
                if not ArtifactListAPI.is_artifact_type_valid(a_type):
                    abort(400, description='invalid artifact type passed')
        if entities:
            for entity in entities:
                if entity not in ['artifact', 'user', 'organization']:
                    abort(400, description='invalid entity passed')

        artifacts, users, organizations = [], [], []
        if 'artifact' in entities:
            artifacts = self.search_artifacts(keywords, artifact_types, page_num)
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

    def post(self):
        """
        Creates a new artifact from the given JSON document, without invoking the importer.
        """
        api_key = request.headers.get('X-API-Key')
        verify_api_key(api_key, config_name)

        j = request.json
        del j["api_key"]
        artifact = object_from_json(db.session, Artifact, j, skip_ids=None)
        db.session.add(artifact)
        try:
            db.session.commit()
        except sqlalchemy.exc.IntegrityError:
            # psycopg2.errors.UniqueViolation:
            traceback.print_exc()
            abort(400, description="duplicate artifact")
        except:
            traceback.print_exc()
            abort(500)
        db.session.expire_all()
        response = jsonify({"id": artifact.id})
        response.status_code = 200
        return response


class ArtifactAPI(Resource):
    def get(self, artifact_id):
        api_key = request.headers.get('X-API-Key')
        if api_key:
            verify_api_key(api_key, config_name)

        artifact = db.session.query(Artifact).filter(
            Artifact.id == artifact_id).first()
        if not artifact:
            abort(404, description='invalid ID for artifact')

        # get average rating for the artifact, number of ratings
        rating_aggregates = db.session.query(ArtifactRatings.artifact_id, func.count(ArtifactRatings.id).label('num_ratings'), func.avg(
            ArtifactRatings.rating).label('avg_rating')).filter(ArtifactRatings.artifact_id == artifact_id).group_by("artifact_id").all()

        ratings = db.session.query(ArtifactRatings, ArtifactReviews).join(ArtifactReviews, and_(
            ArtifactRatings.user_id == ArtifactReviews.user_id,
            ArtifactRatings.artifact_id == ArtifactReviews.artifact_id
        )).filter(ArtifactRatings.artifact_id == artifact_id).all()

        response = jsonify({
            "artifact": ArtifactSchema().dump(artifact),
            "avg_rating": float(rating_aggregates[0][2]) if rating_aggregates else None,
            "num_ratings": rating_aggregates[0][1] if rating_aggregates else 0,
            "num_reviews": len(ratings) if ratings else 0,
            "rating_review": [{
                "rating": ArtifactRatingsSchema(only=("rating",)).dump(rating), 
                "review": ArtifactReviewsSchema(exclude=("artifact_id", "user_id")).dump(review)
                } for rating, review in ratings]
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

    def put(self, artifact_id):
        api_key = request.headers.get('X-API-Key')
        if api_key:
            verify_api_key(api_key, config_name)

        # We can only change unpublished artifacts.
        artifact = db.session.query(Artifact).\
          filter(Artifact.id == artifact_id)\
          .first()
        if not artifact:
            abort(404, description="no such artifact")
        if artifact.publication:
            abort(403, description="artifact already published; cannot modify")
        if not request.is_json:
            abort(400, description="request body must be a JSON representation of an artifact")

        data = request.json
        curations = []
        if "title" in data and artifact.title != data["title"]:
            if not data["title"]:
                abort(400, description="title not nullable")
            artifact.title = data["title"]
            curations.append(ArtifactCuration(
                artifact_id=artifact.id,time=datetime.datetime.now(),
                opdata=json.dumps(
                    [ { "obj":"artifact","op":"set",
                        "data":{ "field":"title","value":data["title"] } } ],
                    separators=(',',':')),
                curator_id=artifact.owner_id))
        if "name" in data and artifact.name != data["name"]:
            artifact.name = data["name"]
            curations.append(ArtifactCuration(
                artifact_id=artifact.id,time=datetime.datetime.now(),
                opdata=json.dumps(
                    [ { "obj":"artifact","op":"set",
                        "data":{ "field":"name","value":data["name"] } } ],
                    separators=(',',':')),
                curator_id=artifact.owner_id))
        if "description" in data and artifact.description != data["description"]:
            artifact.description = data["description"]
            curations.append(ArtifactCuration(
                artifact_id=artifact.id,time=datetime.datetime.now(),
                opdata=json.dumps(
                    [ { "obj":"artifact","op":"set",
                        "data":{ "field":"description","value":data["description"] } } ],
                    separators=(',',':')),
                curator_id=artifact.owner_id))
        if curations:
            db.session.add_all(curations)
        if "publication" in data and data["publication"] is not None:
            notes = None
            if "notes" in data["publication"]:
                notes = data["publication"]
            artifact.publication = ArtifactPublication(
                artifact_id=artifact.id,
                publisher_id=artifact.owner_id,
                time=datetime.datetime.now(),notes=notes)
        db.session.commit()

        response = make_response()
        response.status_code = 200
        return response
