'''
Simple REST api for doing various ant-things.
'''

import logging

from flask import (
    Blueprint,
    request,
    make_response,
    jsonify,
)
from werkzeug.exceptions import (
    BadRequestKeyError,
)
from ..users import (
    User,
    UserError,
)
from ..flask_conf import SECRET_KEY
from ..tokens import (
    validate_token,
    generate_token,
)

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

USER = Blueprint('user', __name__)


#REALM: admin

@USER.route('/user/add', methods=['POST'])
@validate_token(secret_key=SECRET_KEY, realm='admin')
def add_user(current_user):
    '''add a new user to the system'''
    LOG.info('/user/add: called by user %s / realm %s', current_user.email, current_user.realm)
    try:
        user = User.create(
            uname = request.form['uname'],
            email = request.form['email'],
            pword = request.form['pword'],
            realm = request.form['realm'],
        )
        LOG.info('/user/add: created user: %s/%s', user.email, user.realm)
        return jsonify({'message': 'OK'}), 201
    except (AttributeError, BadRequestKeyError) as ex:
        LOG.error('error creating a new user: %s', ex)
        return jsonify({'message': 'ERROR: required fields are not present'}), 401
    except UserError:
        pass
    except Exception as ex: # pylint: disable=broad-except
        LOG.exception('error creating a new user: %s', ex)
    return jsonify({'message': 'ERROR: cannot add user'}), 401


@USER.route('/user/del', methods=['POST'])
@validate_token(secret_key=SECRET_KEY, realm='admin')
def del_user(_admin_user):
    '''delete an existing user'''
    try:
        User.delete(
            email = request.form['email'],
            realm = request.form['realm'],
        )
    except (AttributeError, KeyError, UserError) as ex:
        #expected exceptions
        return jsonify({'message': f'ERROR: {str(ex)}'}), 401

    except Exception as err: # pylint: disable=broad-except
        return jsonify({'message': f'ERROR: {str(err)}'}), 401

    return jsonify({'message': 'OK'}), 201


@USER.route('/user/list', methods=['POST'])
@validate_token(secret_key=SECRET_KEY, realm='admin')
def list_users(_admin_user):
    '''list current user email with their realms'''
    ulist = User.list()
    print(ulist)
    return jsonify({'message': 'OK', 'users': ulist})


@USER.route('/user/auth', methods=['POST'])
def auth_user():
    '''Authenticate the user and issue a JWT (json web token) for api access'''
    err = None
    try:
        email = request.form.get('email')
        pword = request.form.get('pword')
        realm = request.form.get('realm')
        if email is None or pword is None or realm is None:
            raise AttributeError('not all email/pword/realm parameters are present')

        user = User.lookup(email, realm)
        if user.check_pword(pword):
            token = generate_token(SECRET_KEY, email, realm)
            return make_response(jsonify({'token' : token, 'message': 'OK'}), 201)
        err = 'password failed'

    except AttributeError as ex:
        err = str(ex)

    LOG.error('Error authenticating email "%s", realm "%s": %s', email, realm, str(err))
    return jsonify({'message': 'User authentication failed'}), 401
