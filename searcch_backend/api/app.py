# contains app and routes

import os
import logging

from searcch_backend.config import app_config
import flask
from flask import Flask
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow

# set up configurations
app = Flask(__name__, instance_relative_config=True)
config_name = os.getenv("FLASK_ENV","production")
app.config.from_object(app_config[config_name])
if os.getenv('FLASK_INSTANCE_CONFIG_FILE'):
    app.config.from_pyfile(os.getenv('FLASK_INSTANCE_CONFIG_FILE'))


db = SQLAlchemy(app)
ma = Marshmallow(app)
api = Api(app)

if "DEBUG" in app.config and app.config["DEBUG"]:
    import flask
    @app.before_request
    def log_request_info():
        app.logger.debug('Headers: %r', flask.request.headers)
        app.logger.debug('Body: %r', flask.request.get_data())
    import importlib
    dh = flask.logging.default_handler
    for mod in ['searcch_backend','requests','werkzeug']:
        importlib.import_module(mod)
        ml = logging.getLogger(mod)
        ml.setLevel(logging.DEBUG)
        ml.addHandler(dh)


from searcch_backend.api.resources.artifact import ArtifactAPI, ArtifactListAPI
from searcch_backend.api.resources.login import LoginAPI
from searcch_backend.api.resources.rating import RatingAPI, UserRatingAPI
from searcch_backend.api.resources.review import ReviewAPI, ReviewListAPI
from searcch_backend.api.resources.favorite import FavoriteAPI, FavoritesListAPI
from searcch_backend.api.resources.user import UserProfileAPI
from searcch_backend.api.resources.artifact_import import (
    ArtifactImportResourceRoot, ArtifactImportResource)
from searcch_backend.api.resources.importer import (
    ImporterResourceRoot, ImporterResource)

approot = app.config['APPLICATION_ROOT']

api.add_resource(LoginAPI, approot + '/login', endpoint='api.login')

api.add_resource(ArtifactListAPI, approot + '/artifacts', endpoint='api.artifacts')
api.add_resource(ArtifactAPI, approot + '/artifact/<int:artifact_id>', endpoint='api.artifact')

api.add_resource(RatingAPI, approot + '/rating/<int:artifact_id>', endpoint='api.rating')
api.add_resource(UserRatingAPI, approot + '/rating/user/<int:user_id>/artifact/<int:artifact_id>', endpoint='api.userrating')

api.add_resource(ReviewAPI, approot + '/review/<int:artifact_id>', endpoint='api.review')
api.add_resource(ReviewListAPI, approot + '/reviews/<int:artifact_id>', endpoint='api.reviews')

api.add_resource(FavoritesListAPI, approot + '/favorites/<int:user_id>', endpoint='api.favorites')
api.add_resource(FavoriteAPI, approot + '/favorite/<int:artifact_id>', endpoint='api.favorite')

api.add_resource(UserProfileAPI, approot + '/user', endpoint='api.user')

api.add_resource(ArtifactImportResourceRoot, approot + '/artifact/import')
api.add_resource(ArtifactImportResource, approot + '/artifact/import/<int:artifact_import_id>')

api.add_resource(ImporterResourceRoot, approot + '/importer')
api.add_resource(ImporterResource, approot + '/importer/<int:importer_instance_id>')
