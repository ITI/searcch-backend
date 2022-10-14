# logic for /rating

from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.auth import (verify_api_key, verify_token)
from searcch_backend.api.common.sql import object_from_json
from searcch_backend.models.model import *
from searcch_backend.models.schema import *
from flask import abort, jsonify, request, url_for, Blueprint
from flask_restful import reqparse, Resource, fields, marshal
from sqlalchemy import func, desc, asc, sql, or_, and_
import sqlalchemy
import sys
import logging
import math

import base64
import werkzeug

LOG = logging.getLogger(__name__)

class UsersIndexAPI(Resource):

    def __init__(self):
        self.getparse = reqparse.RequestParser()
        self.getparse.add_argument(
            name="can_admin", type=int, required=False,
            help="if 1, show only sessions by users who could have admin privileges")
        self.getparse.add_argument(
            name="allusers", type=int, required=False, default=0, location="args",
            help="if set 1, and if caller is authorized, show all user artifacts")
        self.getparse.add_argument(
            name="owner", type=str, required=False, location="args",
            help="if set, filter by user email and name")
        self.getparse.add_argument(
            name="page", type=int, required=False,
            help="page number for paginated results")
        self.getparse.add_argument(
            name="items_per_page", type=int, required=False, default=20,
            help="results per page if paginated")
        self.getparse.add_argument(
            name="sort", type=str, required=False, default="id",
            choices=("id", "expires_on", "is_admin"),
            help="bad sort field: {error_msg}")
        self.getparse.add_argument(
            name="sort_desc", type=int, required=False, default=1,
            help="if set True, sort descending, else ascending")

        super(UsersIndexAPI, self).__init__()

    def get(self):
        verify_api_key(request)
        login_session = verify_token(request)

        args = self.getparse.parse_args()

        users = db.session.query(User).\
          filter(True if login_session.is_admin and args["allusers"] \
                      else User.id == login_session.user_id)
        users = users.\
          join(Person, User.person_id == Person.id)
        if args["owner"]:
            owner_cond = "%" + args["owner"] + "%"
            users = users.\
              filter(or_(Person.name.ilike(owner_cond),
                         Person.email.ilike(owner_cond)))
        if args["can_admin"] is not None:
            users = users.\
              filter(User.can_admin == bool(args["can_admin"]))
        if not args["sort"]:
            args["sort"] = "id"
        if args["sort_desc"]:
            users = users.\
              order_by(desc(getattr(User,args["sort"])))
        else:
            users = users.\
              order_by(asc(getattr(User,args["sort"])))

        pagination = None
        if "page" in args and args["page"]:
            if args["items_per_page"] <= 0:
                args["items_per_page"] = sys.maxsize
            pagination = users.paginate(
                page=args["page"], error_out=False, per_page=args["items_per_page"])
            users = pagination.items
        else:
            users = users.all()

        # Handle can_admin securely.
        # XXX: there has to be a way for marshmallow to include excluded fields
        # based on context, but I just don't have time right now.
        tmpusers = []
        for u in users:
            tu = UserSchema().dump(u)
            if login_session.is_admin or login_session.user_id == u.id:
                tu["can_admin"] = u.can_admin
            tmpusers.append(tu)

        response_dict = {
            "users": tmpusers
        }
        if pagination:
            response_dict["page"] = pagination.page
            response_dict["total"] = pagination.total
            response_dict["pages"] = int(math.ceil(pagination.total / args["items_per_page"]))

        response = jsonify(response_dict)

        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

class UserProfileAPI(Resource):
    """ 
    UserProfileAPI
    API to:
        - GET: view any user's public profile
        - PUT: edit the current logged-in user's profile
    """

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument(name='name', 
                                   type=str, required=False)
        self.reqparse.add_argument(name='profile_photo', 
                                   type=werkzeug.datastructures.FileStorage, location='files', required=False)
        self.reqparse.add_argument(name='research_interests', 
                                   type=str, required=False)
        self.reqparse.add_argument(name='website', 
                                   type=str, required=False)
        self.reqparse.add_argument(name='email', 
                                   type=str, required=False)

        super(UserProfileAPI, self).__init__()

    def get(self, user_id=None):
        verify_api_key(request)
        login_session = verify_token(request)

        is_logged_in_user = False
        if user_id == login_session.user_id:
            is_logged_in_user = True

        if not user_id:
            user = login_session.user
            is_logged_in_user = True
        else:
            user = db.session.query(User).filter(User.id == user_id).first()
            if not user:
                abort(400, description='User does not exist')

        affiliations = db.session.query(UserAffiliation).\
          filter(UserAffiliation.user_id == user.id).\
          all()

        response = {
                "user": {
                    "id": user.id,
                    "person": {
                        "id": user.person.id,
                        "name": user.person.name,
                        "research_interests": user.person.research_interests,
                        "website": user.person.website,
                        "profile_photo": base64.b64encode(user.person.profile_photo).decode("utf-8") if user.person.profile_photo is not None else ""
                    },
                    "affiliations": UserAffiliationSchema(many=True).dump(affiliations)
                }
            }

        if is_logged_in_user or login_session.is_admin:
            response["user"]["person"]["email"] = user.person.email
            response["user"]["can_admin"] = user.can_admin
        if is_logged_in_user:
            response["user"]["is_admin"] = login_session.is_admin

        response = jsonify(response)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response
    
    def put(self, user_id):
        verify_api_key(request)
        login_session = verify_token(request)

        if user_id != login_session.user_id:
            abort(400, description="insufficient permission to edit user profile")

        args = self.reqparse.parse_args()
        name = args['name']
        profile_photo = None
        if args['profile_photo']:
            profile_photo = args['profile_photo'].read()
        research_interests = args['research_interests']
        website = args['website']
        email = args['email']

        user = login_session.user
        person = db.session.query(Person).filter(Person.id == user.person_id).first()
        
        if name is not None:
            person.name = name
        if research_interests is not None:
            person.research_interests = research_interests
        if website is not None:
            person.website = website
        if profile_photo is not None:
            person.profile_photo = profile_photo
        if email:
            person.email = email

        db.session.commit()

        response = jsonify({"message": "updated user profile"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

class UserArtifactsAPI(Resource):
    def get(self):
        verify_api_key(request)
        login_session = verify_token(request)

        #logged in user record
        user = db.session.query(User).filter(User.id == login_session.user_id).first()

        artifact_schema = ArtifactSchema(many=True)

        owned_artifacts = db.session.query(Artifact).\
          join(ArtifactGroup, Artifact.artifact_group_id == ArtifactGroup.id).\
          join(ArtifactPublication, Artifact.id == ArtifactPublication.artifact_id, isouter=True).\
          filter(or_(and_(ArtifactGroup.owner_id == login_session.user_id,\
                          ArtifactPublication.id != None),\
                     Artifact.owner_id == login_session.user_id)).\
          order_by(Artifact.artifact_group_id, Artifact.ctime.desc()).\
          distinct(Artifact.artifact_group_id)

        owned_artifacts = artifact_schema.dump(owned_artifacts)

        response = jsonify({
            "owned_artifacts": owned_artifacts
        })
        
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response


class UserAffiliationResourceRoot(Resource):
    """
    API to:
        - GET: user's affiliations
        - POST: add a new affiliation
    """

    def get(self):
        verify_api_key(request)
        login_session = verify_token(request)

        user = login_session.user
        affiliations = db.session.query(UserAffiliation).\
          filter(UserAffiliation.user_id == user.id).\
          all()

        response = jsonify({"affiliations": UserAffiliationSchema(many=True).dump(affiliations)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

    def post(self):
        """
        Creates a new affiliation from the given JSON document.
        """
        verify_api_key(request)
        login_session = verify_token(request)

        j = request.json
        if "affiliation" in j:
            j = j["affiliation"]
        if "user" in j:
            abort(400, description="cannot specify user in affiliation; it will be populated from the session")
        if "user_id" in j:
            if j["user_id"] != login_session.user.id:
                abort(400, description="user_id must match user id if provided")
        else:
            j["user_id"] = login_session.user.id

        # Brutal hack for frontend ease: allow POST to just return what's there.
        if "user_id" in j and "org_id" in j:
            affiliation = db.session.query(UserAffiliation).\
              filter(UserAffiliation.user_id == j["user_id"]).\
              filter(UserAffiliation.org_id == j["org_id"]).\
              first()
            if affiliation:
                response = jsonify({"affiliation": UserAffiliationSchema(many=False).dump(affiliation)})
                response.headers.add('Access-Control-Allow-Origin', '*')
                response.status_code = 200
                return response

        affiliation = object_from_json(
            db.session, UserAffiliation, request.json, skip_primary_keys=False,
            error_on_primary_key=False, allow_fk=True)
        db.session.add(affiliation)
        try:
            db.session.commit()
        except sqlalchemy.exc.IntegrityError:
            # psycopg2.errors.UniqueViolation:
            LOG.exception(sys.exc_info()[1])
            abort(400, description="duplicate affiliation")
        except:
            LOG.exception(sys.exc_info()[1])
            abort(500)
        db.session.expire_all()
        response = jsonify({"affiliation": UserAffiliationSchema(many=False).dump(affiliation)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

class UserAffiliationResource(Resource):
    """
    API to:
        - GET: a specific user affiliation
        - DEL: remove a user's affiliation
    """

    def get(self, affiliation_id):
        verify_api_key(request)
        login_session = verify_token(request)

        user = login_session.user
        affiliation = db.session.query(UserAffiliation).\
          filter(UserAffiliation.id == affiliation_id).\
          first()
        if not affiliation:
            abort(404, description="user affiliation does not exist")

        user = affiliation.user
        response_dict = {
            "affiliation": {
                "id": affiliation.id,
                "user_id": affiliation.user_id,
                "org_id": affiliation.org_id,
                "user": {
                    "id": user.id,
                    "person_id": user.person.id,
                    "person": {
                        "id": user.person.id,
                        "name": user.person.name,
                        "research_interests": user.person.research_interests,
                        "website": user.person.website,
                        "profile_photo": base64.b64encode(user.person.profile_photo).decode("utf-8") if user.person.profile_photo is not None else ""
                    },
                },
                "org": OrganizationSchema(many=False).dump(affilation.org) if affiliation.org is not None else None
            }
        }
        if affiliation.user_id == user.id:
            response_dict["affiliation"]["user"]["person"]["email"] = user.person.email

        response = jsonify(response_dict)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

    def delete(self, affiliation_id):
        verify_api_key(request)
        login_session = verify_token(request)

        affiliation = db.session.query(UserAffiliation).\
          filter(UserAffiliation.id == affiliation_id).\
          first()
        if not affiliation:
            abort(404, description="user affiliation does not exist")
        if affiliation.user_id != login_session.user.id:
            abort(400, description="insufficient permission to delete user affiliation; not affiliated user")

        db.session.delete(affiliation)
        db.session.commit()

        response = jsonify({"message": "deleted user affiliation"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response
