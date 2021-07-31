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
                "uri": generate_artifact_uri(artifact.id),
                "doi": artifact.url,
                "type": artifact.type,
                "title": artifact.title,
                "description": artifact.description,
                "avg_rating": float(avg_rating) if avg_rating else None,
                "num_ratings": num_ratings if num_ratings else 0,
                "num_reviews": num_reviews if num_reviews else 0
            }
            artifacts.append(abstract)
    return artifacts

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
                if not ArtifactListAPI.is_artifact_type_valid(a_type):
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

    def post(self):
        """
        Creates a new artifact from the given JSON document, without invoking the importer.
        """
        verify_api_key(request)
        login_session = None
        if has_token(request):
            login_session = verify_token(request)

        data = request.json
        if "artifact" in data:
            data = data["artifact"]
        artifact = object_from_json(db.session, Artifact, data, skip_primary_keys=True,
                                    error_on_primary_key=True)
        if not artifact.ctime:
            artifact.ctime = datetime.datetime.now()
        if login_session:
            artifact.owner = login_session.user
        db.session.add(artifact)
        fake_module_name = "manual"
        if not login_session:
            fake_module_name = "cli-export"
        fake_artifact_import = ArtifactImport(
            type=artifact.type,url=artifact.url,importer_module_name=fake_module_name,
            owner=artifact.owner,ctime=artifact.ctime,status="completed",
            phase="done",artifact=artifact)
        db.session.add(fake_artifact_import)
        try:
            db.session.commit()
        except sqlalchemy.exc.IntegrityError:
            # psycopg2.errors.UniqueViolation:
            ex = sys.exc_info()[1]
            LOG.exception(ex)
            msg = None
            try:
                msg = "%r" % (ex.args)
            except:
                pass
            if not msg:
                msg = "malformed object"
            abort(400, description=msg)
        except:
            LOG.exception(sys.exc_info()[1])
            abort(500)

        db.session.refresh(artifact)

        response = jsonify(dict(artifact=ArtifactSchema().dump(artifact)))
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200

        return response


class ArtifactAPI(Resource):
    def get(self, artifact_id):
        if has_api_key(request):
            verify_api_key(request)

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
        verify_api_key(request)
        login_session = None
        if has_token(request):
            login_session = verify_token(request)

        # We can only change unpublished artifacts.
        artifact = db.session.query(Artifact).\
          filter(Artifact.id == artifact_id)\
          .first()
        if not artifact:
            abort(404, description="no such artifact")
        if login_session and artifact.owner_id != login_session.user_id:
            abort(401, description="insufficient permission to modify artifact")
        if artifact.publication:
            abort(403, description="artifact already published; cannot modify")
        if not request.is_json:
            abort(400, description="request body must be a JSON representation of an artifact")

        data = request.json
        artifact_data = data
        if "artifact" in data:
            artifact_data = data["artifact"]
        if "artifact" in data or len(data) > 1:
            mod_artifact = None
            try:
                # Beware -- in order to use this diff-style comparison,
                # mod_artifact must be a fully-valid object.  For instance, if
                # we do not manually set mod_artifact.owner, and try to display
                # via repr when DEBUG, sqlalchemy will whine that it cannot
                # refresh the object if a refresh is attempted.  This is a bit
                # odd, given that mod_artifact is not in the session, but it is
                # how things work.
                #
                mod_artifact = object_from_json(
                    db.session, Artifact, artifact_data, skip_primary_keys=False,
                    error_on_primary_key=False, should_query=True, allow_fk=True)
                mod_artifact.owner = artifact.owner
            except:
                LOG.exception(sys.exc_info()[1])
                abort(400, description="cannot parse updated artifact: %s" % (
                    repr(sys.exc_info()[1])))
            if not mod_artifact:
                abort(400, description="cannot parse updated artifact")

            curations = None
            try:
                curations = artifact_diff(db.session, artifact, artifact, mod_artifact)
                if curations:
                    db.session.add_all(curations)
                    db.session.add(artifact)
            except (TypeError, ValueError):
                ex = sys.exc_info()[1]
                LOG.exception(ex)
                db.session.rollback()
                if ex.args:
                    abort(500, description="%r" % (ex.args))
                else:
                    abort(500, description="%r" % (ex))
            except:
                ex = sys.exc_info()[1]
                LOG.exception(ex)
                abort(500, description="unexpected internal error")

        if "publication" in data and data["publication"] is not None:
            notes = None
            if "notes" in data["publication"]:
                notes = data["publication"]
            artifact.publication = ArtifactPublication(
                artifact_id=artifact.id,
                publisher_id=artifact.owner_id,
                time=datetime.datetime.now(),notes=notes)
        db.session.commit()
        db.session.refresh(artifact)

        response = jsonify(dict(artifact=ArtifactSchema().dump(artifact)))
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200

        return response


class ArtifactRelationshipResourceRoot(Resource):
    def __init__(self):
        self.getparse = reqparse.RequestParser()
        self.getparse.add_argument(name='artifact_id',
                                   type=int,
                                   required=True,
                                   help='artifact_id to filter')
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument(name='artifact_id',
                                   type=int,
                                   required=True,
                                   help='source artifact')
        self.reqparse.add_argument(name='relation',
                                   type=str,
                                   required=True,
                                   choices=RELATION_TYPES,
                                   help='relation from artifact_id to related_artifact_id')
        self.reqparse.add_argument(name='related_artifact_id',
                                   type=int,
                                   required=True,
                                   help='related artifact')

        super(ArtifactRelationshipResourceRoot, self).__init__()

    def get(self):
        verify_api_key(request)
        login_session = verify_token(request)

        args = self.getparse.parse_args()
        artifact_id = args["artifact_id"]

        # check for valid artifact id
        artifact = db.session.query(Artifact).filter(
            Artifact.id == artifact_id).first()
        if not artifact:
            abort(400, description='invalid artifact ID')

        # get all relationships
        relationships = ArtifactRelationship.query.filter_by(artifact_id=artifact_id).all()

        response = jsonify({"artifact_relationships": ArtifactRelationshipSchema(many=True, exclude=['related_artifact']).dump(relationships)})

        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

    def post(self):
        verify_api_key(request)
        login_session = verify_token(request)

        args = self.reqparse.parse_args()

        artifact_id = args['artifact_id']
        relation = args['relation']
        related_artifact_id = args['related_artifact_id']

        # check for valid artifact id
        artifact = db.session.query(Artifact).filter(
            Artifact.id == artifact_id).first()
        if not artifact:
            abort(400, description='invalid artifact ID')

        # check for valid artifact ownership
        if artifact.owner_id != login_session.user_id:
            abort(400, description='insufficient permission: must own source artifact')
            
        # Check if we are updating an existing relationship
        queried_relationship = ArtifactRelationship.query.filter_by(artifact_id=artifact_id, relation=relation, related_artifact_id=related_artifact_id).first()

        if queried_relationship:
            abort(403, description='relationship already exists')

        # insert the new relation
        new_relationship = ArtifactRelationship(
            artifact_id=artifact_id, relation=relation, related_artifact_id=related_artifact_id)
        db.session.add(new_relationship)
        db.session.commit()
        db.session.refresh(new_relationship)

        response = jsonify({"artifact_relationship": ArtifactRelationshipSchema(many=False, exclude=['related_artifact']).dump(new_relationship)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response


class ArtifactRelationshipResource(Resource):
    def __init__(self):
        self.putparse = reqparse.RequestParser()
        self.putparse.add_argument(
            name='relation',type=str,required=True,choices=RELATION_TYPES,
            help='missing relation between the two artifacts')

        super(ArtifactRelationshipResource, self).__init__()

    def get(self, artifact_relationship_id):
        verify_api_key(request)
        login_session = verify_token(request)

        # check for valid artifact_relationship id
        artifact_relationship = db.session.query(ArtifactRelationship).filter(
            ArtifactRelationship.id == artifact_relationship_id).first()
        if not artifact_relationship:
            abort(400, description='invalid artifact_relationship ID')

        response = jsonify(ArtifactRelationshipSchema(many=False, exclude=['related_artifact']).dump(artifact_relationship))
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

    def put(self, artifact_relationship_id):
        verify_api_key(request)
        login_session = verify_token(request)

        args = self.putparse.parse_args()

        relation = args['relation']

        # check for valid artifact_relationship id
        artifact_relationship = db.session.query(ArtifactRelationship).filter(
            ArtifactRelationship.id == artifact_relationship_id).first()
        if not artifact_relationship:
            abort(400, description='invalid artifact_relationship ID')
        artifact_id = artifact_relationship.artifact_id

        # check for valid artifact_relationship ownership (via artifact)
        artifact_relationship_ownership = db.session.query(Artifact).filter(
            Artifact.id == artifact_id).\
            filter(Artifact.owner_id == login_session.user_id).\
            first()
        if not artifact_relationship_ownership:
            abort(400, description='insufficient permission: must own source artifact')

        artifact_relationship.relation = relation
        db.session.commit()

        response = jsonify({"message": "updated artifact_relationship"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

    def delete(self, artifact_relationship_id):
        verify_api_key(request)
        login_session = verify_token(request)

        # check for valid artifact_relationship id
        artifact_relationship = db.session.query(ArtifactRelationship).filter(
            ArtifactRelationship.id == artifact_relationship_id).first()
        if not artifact_relationship:
            abort(400, description='invalid artifact_relationship ID')
        artifact_id = artifact_relationship.artifact_id

        # check for valid artifact ownership
        artifact_ownership = db.session.query(Artifact).filter(
            Artifact.id == artifact_id).\
            filter(Artifact.owner_id == login_session.user_id).\
            first()
        if not artifact_ownership:
            abort(400, description='insufficient permission: must own source artifact')

        db.session.delete(artifact_relationship)
        db.session.commit()
        response = jsonify({"message": "deleted artifact_relationship"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response


class ArtifactRecommendationAPI(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument(name='page',
                                   type=int,
                                   required=False,
                                   default=1,
                                   help='page number for paginated results')
        

        super(ArtifactRecommendationAPI, self).__init__()
    
    def get(self, artifact_id):
        verify_api_key(request)
        login_session = verify_token(request)
        args = self.reqparse.parse_args()
        page_num = args['page']

        # check for valid artifact id
        artifact = db.session.query(Artifact).filter(
            Artifact.id == artifact_id).first()
        if not artifact:
            abort(400, description='invalid artifact ID')

        top_keywords = db.session.query(ArtifactMetadata.value).filter(
            ArtifactMetadata.artifact_id == artifact_id, ArtifactMetadata.name == "top_ngram_keywords").first()
        if not top_keywords:
            response = jsonify(
                {"message": "The artifact doesnt have any top rated keywords"})
        else:
            top_keywords_list = json.loads(top_keywords[0])
            keywords = []
            for keyword in top_keywords_list:
                keywords.append(keyword[0])
            artifacts = search_artifacts(" or ".join(keywords), ARTIFACT_TYPES, page_num)
            response = jsonify({"artifacts": artifacts})



        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response
