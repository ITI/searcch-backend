# contains app and routes

import os
import logging

from searcch_backend.config import app_config
import flask
from flask import Flask
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate

# set up configurations
app = Flask(__name__, instance_relative_config=True)
config_name = os.getenv("FLASK_ENV", "development")
app.config.from_object(app_config[config_name])
if os.getenv('FLASK_INSTANCE_CONFIG_FILE'):
    app.config.from_pyfile(os.getenv('FLASK_INSTANCE_CONFIG_FILE'))


db = SQLAlchemy(app)
migrate = Migrate(app, db, directory="searcch_backend/migrations")
ma = Marshmallow(app)
api = Api(app)

#
# If gunicorn, propagate its logging config to flask.
#
slog = None
if flask.logging.default_handler.level == 0:
    slog = logging.getLogger('gunicorn.error')
if __name__ != "__main__" and slog and slog != app.logger:
    app.logger.handlers = slog.handlers
    app.logger.setLevel(slog.level)

if "DEBUG" in app.config and app.config["DEBUG"]:
    @app.before_request
    def log_request_info():
        app.logger.debug('Headers: %r', repr(flask.request.headers))
        cstr = flask.request.get_data(as_text=True)
        if cstr:
            cstr = cstr[:32]
            app.logger.debug('Body: %r', cstr)

app.logger.debug("flask config: %r",app.config)

if "DB_AUTO_MIGRATE" in app.config and app.config["DB_AUTO_MIGRATE"]:
    with app.app_context():
        import alembic
        alembic.command.upgrade(migrate.get_config(),"head")

from searcch_backend.api.resources.artifact import ArtifactAPI, ArtifactListAPI, ArtifactRelationshipAPI, ArtifactRecommendationAPI
from searcch_backend.api.resources.organization import OrganizationAPI, OrganizationListAPI
from searcch_backend.api.resources.login import LoginAPI
from searcch_backend.api.resources.rating import RatingAPI, UserRatingAPI
from searcch_backend.api.resources.review import ReviewAPI, ReviewListAPI
from searcch_backend.api.resources.favorite import FavoriteAPI, FavoritesListAPI
from searcch_backend.api.resources.user import UserProfileAPI
from searcch_backend.api.resources.dashboard import UserDashboardAPI, ArtifactStatsAPI
from searcch_backend.api.resources.interests import InterestsListAPI
from searcch_backend.api.resources.artifact_import import (
    ArtifactImportResourceRoot, ArtifactImportResource)
from searcch_backend.api.resources.importer import (
    ImporterResourceRoot, ImporterResource)

approot = app.config['APPLICATION_ROOT']

api.add_resource(LoginAPI, approot + '/login', endpoint='api.login')

api.add_resource(ArtifactListAPI, approot + '/artifacts', endpoint='api.artifacts')
api.add_resource(ArtifactAPI, approot + '/artifact/<int:artifact_id>', endpoint='api.artifact')
api.add_resource(ArtifactRelationshipAPI, approot + '/artifact/relationship/<int:artifact_id>', endpoint='api.artifact_relationship')
api.add_resource(ArtifactRecommendationAPI, approot + '/artifact/recommendation/<int:artifact_id>', endpoint='api.artifact_recommender')

api.add_resource(OrganizationListAPI, approot + '/organizations', endpoint='api.organizations')
api.add_resource(OrganizationAPI, approot + '/organization/<int:org_id>', endpoint='api.organization')

api.add_resource(InterestsListAPI, approot + '/interests', endpoint='api.interests')

api.add_resource(RatingAPI, approot + '/rating/<int:artifact_id>', endpoint='api.rating')
api.add_resource(UserRatingAPI, approot + '/rating/user/<int:user_id>/artifact/<int:artifact_id>', endpoint='api.userrating')

api.add_resource(ReviewAPI, approot + '/review/<int:artifact_id>', endpoint='api.review')
api.add_resource(ReviewListAPI, approot + '/reviews/<int:artifact_id>', endpoint='api.reviews')

api.add_resource(FavoritesListAPI, approot + '/favorites/<int:user_id>', endpoint='api.favorites')
api.add_resource(FavoriteAPI, approot + '/favorite/<int:artifact_id>', endpoint='api.favorite')

api.add_resource(UserProfileAPI, approot + '/user', endpoint='api.user')
api.add_resource(UserDashboardAPI, approot + '/dashboard', endpoint='api.dashboard')
api.add_resource(ArtifactStatsAPI, approot + '/dashboard/artifact/stats', endpoint='api.dashboard_artifact_stats')

api.add_resource(ArtifactImportResourceRoot, approot + '/artifact/imports', endpoint='api.artifact_imports')
api.add_resource(ArtifactImportResource, approot + '/artifact/import/<int:artifact_import_id>', endpoint='api.artifact_import')

api.add_resource(ImporterResourceRoot, approot + '/importers', endpoint='api.importers')
api.add_resource(ImporterResource, approot + '/importer/<int:importer_instance_id>', endpoint='api.importer')
