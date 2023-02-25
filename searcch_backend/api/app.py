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
from flask_mail import Mail

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
mail = Mail(app)

@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.expire_all()
    db.session.remove()

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

from searcch_backend.api.resources.artifact import (
    ArtifactAPI, ArtifactIndexAPI,
    ArtifactRelationshipResourceRoot, ArtifactRelationshipResource, ArtifactOwnerRequestAPI, ArtifactOwnerRequestsAPI)
from searcch_backend.api.resources.artifact_compare import ArtifactCompareAPI
from searcch_backend.api.resources.artifact_search import ArtifactSearchIndexAPI, ArtifactRecommendationAPI
from searcch_backend.api.resources.artifact_request import ArtifactRequestAPI
from searcch_backend.api.resources.artifact_view import ArtifactViewAPI
from searcch_backend.api.resources.organization import OrganizationAPI, OrganizationListAPI
from searcch_backend.api.resources.login import LoginAPI
from searcch_backend.api.resources.session import (
    SessionResourceRoot, SessionResource)
from searcch_backend.api.resources.rating import RatingAPI, UserRatingAPI
from searcch_backend.api.resources.review import ReviewAPI, ReviewListAPI
from searcch_backend.api.resources.favorite import FavoriteAPI, FavoritesListAPI
from searcch_backend.api.resources.user import (
    UserProfileAPI, UserArtifactsAPI, UserAffiliationResourceRoot,
    UserAffiliationResource, UsersIndexAPI)
from searcch_backend.api.resources.dashboard import UserDashboardAPI, ArtifactStatsAPI
from searcch_backend.api.resources.interests import InterestsListAPI
from searcch_backend.api.resources.artifact_import import (
    ArtifactImportResourceRoot, ArtifactImportResource)
from searcch_backend.api.resources.importer import (
    ImporterResourceRoot, ImporterResource)
from searcch_backend.api.resources.schema import (
    SchemaArtifactAPI, SchemaAffiliationAPI)
from searcch_backend.api.resources.badge import BadgeResourceRoot, BadgeResource
from searcch_backend.api.resources.license import LicenseResourceRoot, LicenseResource
from searcch_backend.api.common.scheduled_tasks import UpdateStatsViews
from searcch_backend.api.resources.dua import DUAResource
from searcch_backend.api.resources.label import LabelsResource

approot = app.config['APPLICATION_ROOT']

api.add_resource(LoginAPI, approot + '/login', endpoint='api.login')

api.add_resource(SessionResourceRoot, approot + '/sessions', endpoint='api.sessions')
api.add_resource(SessionResource, approot + '/session/<int:session_id>', endpoint='api.session')

api.add_resource(ArtifactIndexAPI, approot + '/artifacts', endpoint='api.artifacts')
api.add_resource(ArtifactAPI, approot + '/artifact/<int:artifact_group_id>', approot + '/artifact/<int:artifact_group_id>/<int:artifact_id>', endpoint='api.artifact')
api.add_resource(ArtifactCompareAPI, approot + '/artifact/compare/<int:artifact_group_id>/<int:artifact_id>', endpoint='api.artifact_compare')
api.add_resource(ArtifactSearchIndexAPI, approot + '/artifact/search', endpoint='api.artifact_search')
api.add_resource(ArtifactRequestAPI, approot + '/artifact/request/<int:artifact_group_id>', approot + '/artifact/request/<int:artifact_group_id>/<int:artifact_id>', endpoint='api.artifact_request')
api.add_resource(ArtifactViewAPI, approot + '/artifact/view/<int:artifact_group_id>', approot + '/artifact/view/<int:artifact_group_id>/<int:artifact_id>', endpoint='api.artifact_view')
api.add_resource(ArtifactRelationshipResourceRoot, approot + '/artifact/relationships', endpoint='api.artifact_relationships')
api.add_resource(ArtifactRelationshipResource, approot + '/artifact/relationship/<int:artifact_relationship_id>', endpoint='api.artifact_relationship')
api.add_resource(ArtifactRecommendationAPI, approot + '/artifact/recommendation/<int:artifact_group_id>/<int:artifact_id>', endpoint='api.artifact_recommender')

api.add_resource(ArtifactOwnerRequestAPI, approot + '/artifact/request/owner/<int:artifact_group_id>', endpoint='api.artifact_request_owner')
api.add_resource(ArtifactOwnerRequestsAPI, approot + '/artifact/requests/owner', endpoint='api.artifact_requests_owner')

api.add_resource(OrganizationListAPI, approot + '/organizations', endpoint='api.organizations')
api.add_resource(OrganizationAPI, approot + '/organization/<int:org_id>', endpoint='api.organization')

api.add_resource(InterestsListAPI, approot + '/interests', endpoint='api.interests')

api.add_resource(RatingAPI, approot + '/rating/<int:artifact_group_id>', endpoint='api.rating')
api.add_resource(UserRatingAPI, approot + '/rating/user/<int:user_id>/artifact/<int:artifact_group_id>', endpoint='api.userrating')

api.add_resource(ReviewAPI, approot + '/review/<int:artifact_group_id>', endpoint='api.review')
api.add_resource(ReviewListAPI, approot + '/reviews/<int:artifact_group_id>', endpoint='api.reviews')

api.add_resource(FavoritesListAPI, approot + '/favorites/<int:user_id>', endpoint='api.favorites')
api.add_resource(FavoriteAPI, approot + '/favorite/<int:artifact_group_id>', endpoint='api.favorite')

api.add_resource(UsersIndexAPI, approot + '/users', endpoint='api.users')
api.add_resource(UserProfileAPI, approot + '/user/<int:user_id>', approot + '/user', endpoint='api.user')
api.add_resource(UserArtifactsAPI, approot + '/user/artifacts', endpoint='api.user_artifacts')

api.add_resource(UserAffiliationResourceRoot, approot + '/user/affiliations', endpoint='api.user_affiliations')
api.add_resource(UserAffiliationResource, approot + '/user/affiliation/<int:affiliation_id>', endpoint='api.user_affiliation')

api.add_resource(UserDashboardAPI, approot + '/dashboard', endpoint='api.dashboard')
api.add_resource(ArtifactStatsAPI, approot + '/dashboard/artifact/stats', endpoint='api.dashboard_artifact_stats')

api.add_resource(ArtifactImportResourceRoot, approot + '/artifact/imports', endpoint='api.artifact_imports')
api.add_resource(ArtifactImportResource, approot + '/artifact/import/<int:artifact_import_id>', endpoint='api.artifact_import')

api.add_resource(ImporterResourceRoot, approot + '/importers', endpoint='api.importers')
api.add_resource(ImporterResource, approot + '/importer/<int:importer_instance_id>', endpoint='api.importer')

api.add_resource(SchemaArtifactAPI, approot + "/schema/artifact", endpoint='api.schema_artifact')
api.add_resource(SchemaAffiliationAPI, approot + "/schema/affiliation", endpoint='api.schema_affiliation')

api.add_resource(BadgeResourceRoot, approot + '/badges', endpoint='api.badges')
api.add_resource(BadgeResource, approot + '/badge/<int:badge_id>', endpoint='api.badge')

api.add_resource(LicenseResourceRoot, approot + '/licenses', endpoint='api.licenses')
api.add_resource(LicenseResource, approot + '/license/<int:org_id>', endpoint='api.license')

api.add_resource(DUAResource, approot + '/dua/<int:artifact_group_id>', endpoint='api.dua')

api.add_resource(LabelsResource, approot + '/labels/<int:artifact_id>', endpoint='api.label')