# logic for /rating

from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.auth import (verify_api_key, verify_token)
from searcch_backend.api.common.sql import object_from_json
from searcch_backend.models.model import *
from searcch_backend.models.schema import *
from flask import abort, jsonify, request, url_for, Blueprint
from flask_restful import reqparse, Resource, fields, marshal
from sqlalchemy import func, desc, sql
import sqlalchemy
import sys
import logging

import base64
import werkzeug

LOG = logging.getLogger(__name__)

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
        
        organizations = db.session.query(Organization).filter(Organization.id.in_(
                db.session.query(Affiliation.org_id).filter(Affiliation.person_id == user.person.id)))
        
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
                    "organization": OrganizationSchema(many=True).dump(organizations)
                }
            }

        if is_logged_in_user:
            response["user"]["person"]["email"] = user.person.email

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
        owned_artifacts = db.session.query(Artifact).filter(Artifact.owner_id == login_session.user_id)

        response = jsonify({
            "owned_artifacts": artifact_schema.dump(owned_artifacts)
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
        affiliations = db.session.query(Affiliation).\
          filter(Affiliation.person_id == user.person.id).\
          all()

        response = jsonify({"affiliations": AffiliationSchema(many=True).dump(affiliations)})
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
        if "person" in j:
            abort(400, description="cannot specify person in affiliation; it will be populated from the session user's person")
        if "person_id" in j:
            if j["person_id"] != login_session.user.person.id:
                abort(400, description="person_id must match user person_id if provided")
        else:
            j["person_id"] = login_session.user.person.id

        affiliation = object_from_json(
            db.session, Affiliation, request.json, skip_primary_keys=False,
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
        response = jsonify({"affiliation": AffiliationSchema(many=False).dump(affiliation)})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response
