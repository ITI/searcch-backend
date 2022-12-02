#!/bin/env python3
'''
Simple REST api for doing various ant-things.
'''

import os

from flask import (
    Flask,
)
from .users import (
    init_db,
)
from .paths.user import USER
from .paths.trac import TRAC

_deployment_path = os.path.realpath(os.path.dirname(__file__)+'/..')
APP = Flask(__name__, instance_path=_deployment_path + '/instance')
APP.config.from_pyfile('flask_conf.py')
init_db(APP)


@APP.route('/')
def index():
    '''Placeholder; not sure we want public documentation'''
    return "hello, world\n"

#/user/...
APP.register_blueprint(USER)

#/trac/...
APP.register_blueprint(TRAC)

if __name__ == "__main__":
    APP.run()
