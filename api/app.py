# contains app and routes

from config import app_config
from flask import Flask
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import os


# set up configurations
app = Flask(__name__, instance_relative_config=True)
config_name = os.getenv('FLASK_CONFIG')
app.config.from_object(app_config[config_name])
app.config.from_object('config')
app.config.from_pyfile('config.py')

db = SQLAlchemy(app)
ma = Marshmallow(app)
api = Api(app)


from api.resources.artifact import ArtifactAPI, ArtifactListAPI
from api.resources.login import LoginAPI
from api.resources.rating import RatingAPI
from api.resources.review import ReviewAPI
from api.resources.favorite import FavoriteAPI

api.add_resource(LoginAPI, '/login')
api.add_resource(ArtifactListAPI, '/artifacts')
api.add_resource(ArtifactAPI, '/artifacts/<int:artifact_id>')
api.add_resource(RatingAPI, '/rating/<int:artifact_id>')
api.add_resource(ReviewAPI, '/review/<int:artifact_id>')
api.add_resource(FavoriteAPI, '/favorite/<int:artifact_id>')