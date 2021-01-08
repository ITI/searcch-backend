# contains app and routes

from searcch_backend.config import app_config
from flask import Flask
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import os

# set up configurations
app = Flask(__name__, instance_relative_config=True)
config_name = os.getenv('FLASK_CONFIG')
app.config.from_object(app_config[config_name])
app.config.from_object('searcch_backend.config')
if os.getenv('FLASK_INSTANCE_CONFIG_FILE'):
    app.config.from_pyfile(os.getenv('FLASK_INSTANCE_CONFIG_FILE'))
else:
    app.config.from_pyfile('config.py')


db = SQLAlchemy(app)
ma = Marshmallow(app)
api = Api(app)


from searcch_backend.api.resources.artifact import ArtifactAPI, ArtifactListAPI
from searcch_backend.api.resources.login import LoginAPI
from searcch_backend.api.resources.rating import RatingAPI, UserRatingAPI
from searcch_backend.api.resources.review import ReviewAPI, ReviewListAPI
from searcch_backend.api.resources.favorite import FavoriteAPI, FavoritesListAPI
from searcch_backend.api.resources.user import UserProfileAPI

api.add_resource(LoginAPI, app.config['APPLICATION_ROOT'] + '/login', endpoint='api.login')

api.add_resource(ArtifactListAPI, app.config['APPLICATION_ROOT'] + '/artifacts', endpoint='api.artifacts')
api.add_resource(ArtifactAPI, app.config['APPLICATION_ROOT'] + '/artifact/<int:artifact_id>', endpoint='api.artifact')

api.add_resource(RatingAPI, app.config['APPLICATION_ROOT'] + '/rating/<int:artifact_id>', endpoint='api.rating')
api.add_resource(UserRatingAPI, app.config['APPLICATION_ROOT'] + '/rating/user/<int:user_id>/artifact/<int:artifact_id>', endpoint='api.userrating')

api.add_resource(ReviewAPI, app.config['APPLICATION_ROOT'] + '/review/<int:artifact_id>', endpoint='api.review')
api.add_resource(ReviewListAPI, app.config['APPLICATION_ROOT'] + '/reviews/<int:artifact_id>', endpoint='api.reviews')

api.add_resource(FavoritesListAPI, app.config['APPLICATION_ROOT'] + '/favorites/<int:user_id>', endpoint='api.favorites')
api.add_resource(FavoriteAPI, app.config['APPLICATION_ROOT'] + '/favorite/<int:artifact_id>', endpoint='api.favorite')

api.add_resource(UserProfileAPI, app.config['APPLICATION_ROOT'] + '/user', endpoint='api.user')
