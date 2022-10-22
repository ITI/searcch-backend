# logic for /admin

from searcch_backend.api.app import db
from searcch_backend.models.model import *
from searcch_backend.models.schema import *
from flask import abort, jsonify, request
from flask_restful import reqparse, Resource
from searcch_backend.api.common.auth import (verify_api_key, verify_token)
import logging

LOG = logging.getLogger(__name__)


class AdminUpdatePrivileges(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument(name='can_admin',
                                   type=str,
                                   required=True,
                                   default=None,
                                   help='admin privilege of user')
        self.reqparse.add_argument(name='user_id',
                                   type=int,
                                   required=True,
                                   default=None,
                                   help='user_id of user to update')
        

        super(AdminUpdatePrivileges, self).__init__()
    
    def put(self):
        verify_api_key(request)
        login_session = verify_token(request)
        args = self.reqparse.parse_args()
        can_admin = args['can_admin']
        user_id = args['user_id']

        # check if requesting user is an admin
        admin_user = db.session.query(User.can_admin)\
            .filter(User.id == login_session.user_id)\
            .first()
        if not admin_user:
            abort(400, description='invalid requesting user id')
        if not admin_user.can_admin:
            abort(400, description='requesting user is not an admin')

        if can_admin is not None and user_id is not None:
            # do not allow admin to modify their own admin privileges
            if user_id == login_session.user_id:
                abort(400, description='cannot modify your own admin privileges')
            # update can_admin
            user = db.session.query(User)\
                .filter(User.id == user_id)\
                .first()
            if not user:
                abort(400, description='invalid user_id')
            user.can_admin = True if can_admin == 't' else False
            db.session.commit()
            response = jsonify({'message': 'admin privileges updated'})
        else:
            abort(400, description='invalid request')

        response.headers.add('Access-Control-Allow-Origin', '*')
        response.status_code = 200
        return response
