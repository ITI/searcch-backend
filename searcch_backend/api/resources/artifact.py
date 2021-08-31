# logic for /artifacts

from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.sql import (object_from_json, artifact_diff)
from searcch_backend.api.common.auth import (verify_api_key, has_api_key, has_token, verify_token)
from searcch_backend.models.model import *
from searcch_backend.models.schema import *
from flask import abort, jsonify, request, make_response, Blueprint, url_for, Response
from flask_restful import reqparse, Resource, fields, marshal
import sqlalchemy
from sqlalchemy import func, desc, asc, sql, and_, or_
import datetime
import json
import sys
import logging
import math

LOG = logging.getLogger(__name__)

class ArtifactIndexAPI(Resource):

    def __init__(self):
        self.getparse = reqparse.RequestParser()
        self.getparse.add_argument(
            name="type", type=str, required=False, action="append",
            help="missing type to filter results")
        self.getparse.add_argument(
            name="published", type=int, required=False,
            help="if 1, show only published artifacts")
        self.getparse.add_argument(
            name="allusers", type=int, required=False, default=0, location="args",
            help="if set 1, and if caller is authorized, show all user artifacts")
        self.getparse.add_argument(
            name="owner", type=str, required=False, location="args",
            help="if set, filter by user email and name")
        self.getparse.add_argument(
            name="short_view_include", type=str, required=False,
            help="Return only fields, unless relations are specified in this field (valid: %s)" % (
                ",".join(Artifact.__mapper__.relationships.keys())))
        self.getparse.add_argument(
            name="page", type=int, required=False,
            help="page number for paginated results")
        self.getparse.add_argument(
            name="items_per_page", type=int, required=False, default=20,
            help="results per page if paginated")
        self.getparse.add_argument(
            name="sort", type=str, required=False, default="id",
            choices=("id", "type", "title", "url", "ctime", "mtime" ),
            help="bad sort field: {error_msg}")
        self.getparse.add_argument(
            name="sort_desc", type=int, required=False, default=1,
            help="if set True, sort descending, else ascending")

        super(ArtifactIndexAPI, self).__init__()

    def get(self):
        verify_api_key(request)
        login_session = verify_token(request)

        args = self.getparse.parse_args()
        artifact_types = args['type']

        if artifact_types:
            for a_type in artifact_types:
                if a_type not in ARTIFACT_TYPES:
                    abort(400, description='invalid artifact type passed')

        artifacts = db.session.query(Artifact).\
          filter(True if login_session.is_admin and args["allusers"] \
                      else Artifact.owner_id == login_session.user_id)
        if artifact_types:
            artifacts = artifacts.\
              filter(Artifact.type.in_(artifact_types))
        if args["published"] == 1:
            artifacts = artifacts.\
              filter(Artifact.publication != None)
        elif args["published"] == 0:
            artifacts = artifacts.\
              filter(Artifact.publication == None)
        if args["owner"]:
            owner_cond = "%" + args["owner"] + "%"
            artifacts = artifacts.\
              join(User, Artifact.owner_id == User.id).\
              join(Person, User.person_id == Person.id)
            artifacts = artifacts.\
              filter(or_(Person.name.ilike(owner_cond),
                         Person.email.ilike(owner_cond)))
        if not args["sort"]:
            args["sort"] = "id"
        if args["sort_desc"]:
            artifacts = artifacts.\
              order_by(desc(getattr(Artifact,args["sort"])))
        else:
            artifacts = artifacts.\
              order_by(asc(getattr(Artifact,args["sort"])))

        pagination = None
        if "page" in args and args["page"]:
            if args["items_per_page"] <= 0:
                args["items_per_page"] = sys.maxsize
            pagination = artifacts.paginate(
                page=args["page"], error_out=False, per_page=args["items_per_page"])
            artifacts = pagination.items
        else:
            artifacts = artifacts.all()

        exclude = None
        if args["short_view_include"] is not None:
            sva = args["short_view_include"].split(",")
            exclude = list(Artifact.__mapper__.relationships.keys())
            for x in sva:
                if not x in exclude:
                    abort(401, description="invalid short_view_include relation")
                exclude.remove(x)

        response_dict = {
            "artifacts": ArtifactSchema(
                many=True,exclude=exclude).dump(artifacts)
        }
        if pagination:
            response_dict["page"] = pagination.page
            response_dict["total"] = pagination.total
            response_dict["pages"] = int(math.ceil(pagination.total / args["items_per_page"]))

        response = jsonify(response_dict)

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
                                    error_on_primary_key=False, allow_fk=True)
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

        # We can only change unpublished artifacts unless admin.
        artifact = db.session.query(Artifact).\
          filter(Artifact.id == artifact_id)\
          .first()
        if not artifact:
            abort(404, description="no such artifact")
        if login_session and not login_session.is_admin and artifact.owner_id != login_session.user_id:
            abort(401, description="insufficient permission to modify artifact")
        if artifact.publication and not login_session.is_admin:
            abort(403, description="artifact already published; cannot modify")
        if not request.is_json:
            abort(400, description="request body must be a JSON representation of an artifact")

        data = request.json
        artifact_data = data
        if "artifact" in data:
            artifact_data = data["artifact"]
        if "artifact" in data or len(data) > 1:
            mod_artifact = None
            with db.session.no_autoflush:
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
                    curator = login_session.user if login_session else artifact.owner
                    curations = artifact_diff(db.session, curator, artifact, artifact, mod_artifact)
                    if curations:
                        artifact.mtime = datetime.datetime.now()
                        db.session.add_all(curations)
                        db.session.add(artifact)
                except sqlalchemy.exc.IntegrityError:
                    ex = sys.exc_info()[1]
                    LOG.exception(ex)
                    abort(400, description="malformed input: %r" % (ex.args,))
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
                    db.session.rollback()
                    abort(500, description="unexpected internal error")

        if "publication" in data and data["publication"] is not None \
          and not artifact.publication:
            notes = None
            if "notes" in data["publication"]:
                notes = data["publication"]
            now = datetime.datetime.now()
            artifact.publication = ArtifactPublication(
                artifact_id=artifact.id,
                publisher_id=artifact.owner_id,
                time=now,notes=notes)
            # Automatically archive the artifact.
            artifact_import = db.session.query(ArtifactImport).\
              filter(ArtifactImport.artifact_id == artifact.id).\
              first()
            if artifact_import:
                artifact_import.archived = True
            artifact.mtime = now
        db.session.commit()
        db.session.refresh(artifact)

        response = jsonify(dict(artifact=ArtifactSchema().dump(artifact)))
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200

        return response

    def delete(self, artifact_id):
        verify_api_key(request)
        login_session = verify_token(request)

        # We can only delete unpublished artifacts.
        artifact = db.session.query(Artifact).\
          filter(Artifact.id == artifact_id).\
          first()
        if not artifact:
            abort(404, description="no such artifact")
        if not (login_session.is_admin or artifact.owner_id == login_session.user_id):
            abort(401, description="insufficient permission to delete artifact")
        if artifact.publication and not login_session.is_admin:
            abort(403, description="artifact already published; cannot delete")

        # If currently importing, delete that first, and commit:
        artifact_import = db.session.query(ArtifactImport).\
          filter(ArtifactImport.artifact_id == artifact_id).\
          first()
        if artifact_import:
            schedule = db.session.query(ImporterSchedule).\
              filter(ImporterSchedule.artifact_import_id == artifact_import.id).\
              first()
            if schedule:
                db.session.delete(schedule)
            db.session.delete(artifact_import)
            db.session.commit()

        db.session.refresh(artifact)
        db.session.refresh(login_session)

        for af in getattr(artifact, "files", []):
            for afm in getattr(af, "members", []):
                db.session.delete(afm)
            af.members = []
            db.session.delete(af)
        artifact.files = []
        many = [ "meta", "tags", "curations", "affiliations", "relationships", "releases",
                 "badges", "ratings", "reviews", "favorites" ]
        for field in many:
            for x in getattr(artifact, field, []):
                db.session.delete(x)
            setattr(artifact, field, [])
        single = [ "publication" ]
        for field in single:
            x = getattr(artifact, field, None)
            if x:
                db.session.delete(x)
                setattr(artifact, field, None)

        db.session.delete(artifact)
        try:
            db.session.commit()
        except:
            LOG.error("failed to delete artifact %r", artifact_id)
            LOG.exception(sys.exc_info()[1])
            abort(500, description="failed to delete artifact %r" % (artifact_id,))

        return Response(status=200)


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
        if artifact.owner_id != login_session.user_id and not login_session.is_admin:
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
            filter(True if login_session.is_admin else Artifact.owner_id == login_session.user_id).\
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
            filter(True if login_session.is_admin else Artifact.owner_id == login_session.user_id).\
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
