# logic for /rating

from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.auth import (verify_api_key, verify_token)
from searcch_backend.models.model import *
from searcch_backend.models.schema import *
from flask import abort, jsonify, request, url_for, Blueprint
from flask_restful import reqparse, Resource, fields, marshal
from sqlalchemy import func, desc, sql

import base64
import werkzeug

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
        self.reqparse.add_argument(name='userid', 
                                   type=int, required=False, help='missing user ID')
        self.reqparse.add_argument(name='profile_photo', 
                                   type=werkzeug.datastructures.FileStorage, location='files', required=False)
        self.reqparse.add_argument(name='research_interests', 
                                   type=str, required=False)
        self.reqparse.add_argument(name='website', 
                                   type=str, required=False)
        self.reqparse.add_argument(name='email', 
                                   type=str, required=False)

        super(UserProfileAPI, self).__init__()

    def get(self):
        verify_api_key(request)
        login_session = verify_token(request)
        args = self.reqparse.parse_args()
        user_id = args['userid']
        
        if not user_id:
            user = login_session.user
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

        if not user_id:
            response["user"]["person"]["email"] = user.person.email
            response = jsonify(response)
        else:
            response = jsonify(response)

        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response
    
    def put(self):
        verify_api_key(request)
        login_session = verify_token(request)

        args = self.reqparse.parse_args()
        name = args['name']
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