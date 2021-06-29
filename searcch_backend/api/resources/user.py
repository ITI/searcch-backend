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
        self.reqparse.add_argument(name='profile_photo', 
                                   type=werkzeug.datastructures.FileStorage, location='files', required=False)
        self.reqparse.add_argument(name='research_interests', 
                                   type=str, required=False)
        self.reqparse.add_argument(name='website', 
                                   type=str, required=False)

        super(UserProfileAPI, self).__init__()

    def get(self):
        verify_api_key(request)
        login_session = verify_token(request)

        user = login_session.user
        organizations = db.session.query(Organization).filter(Organization.id.in_(
            db.session.query(Affiliation.org_id).filter(Affiliation.person_id == user.person.id)))
        response = jsonify({
            "user": {
                "id": user.id,
                "person": {
                    "email": user.person.email,
                    "id": user.person.id,
                    "name": user.person.name,
                    "research_interests": user.person.research_interests,
                    "website": user.person.website,
                    "profile_photo": base64.b64encode(user.person.profile_photo).decode("utf-8") if user.person.profile_photo is not None else ""
                },
                "organization": OrganizationSchema(many=True).dump(organizations)
            }
        })
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

        db.session.commit()

        response = jsonify({"message": "updated user profile"})
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response

