# logic for /rating

from searcch_backend.api.app import db, config_name
from searcch_backend.api.common.auth import *
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
        self.reqparse.add_argument(name='token', 
                                   type=str, required=True, default='',
                                   help='missing SSO token from auth provider in post request')
        self.reqparse.add_argument(name='userid', 
                                   type=int, required=True, help='missing user ID')
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
        args = self.reqparse.parse_args()
        user_id = args['userid']

        # verify session credentials
        api_key = request.headers.get('X-API-Key')
        verify_api_key(api_key, config_name)
        if config_name == 'production':
            sso_token = args['token']
            if not verify_token(sso_token):
                abort(401, "no active login session found. please login to continue")

        user = db.session.query(User).filter(User.id == user_id).first()        
        response = jsonify({
            "user": {
                "id": user.id,
                "person": {
                    "email": user.person.email,
                    "id": user.person.id,
                    "name": user.person.name,
                    "research_interests": user.person.research_interests,
                    "website": user.person.website,
                    "profile_photo": base64.b64encode(user.person.profile_photo).decode("utf-8")
                }
            }
        })
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response
    
    def put(self):
        args = self.reqparse.parse_args()
        user_id = args['userid']
        name = args['name']
        profile_photo = args['profile_photo'].read()
        research_interests = args['research_interests']
        website = args['website']

        api_key = request.headers.get('X-API-Key')
        verify_api_key(api_key, config_name)
        if config_name == 'production':
            sso_token = args['token']
            if not verify_token(sso_token):
                abort(401, "no active login session found. please login to continue")

            # verify that userid passed is the same as the logged-in user
            active_login_session = db.session.query(Sessions).filter(
                Sessions.sso_token == sso_token).first()
            if active_login_session.user_id != user_id:
                abort(401, "cannot edit profile for another user")

        user = db.session.query(User).filter(User.id == user_id).first()
        if not user:
            abort(400, description='no user found with given user ID')
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

