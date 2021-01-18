class Config(object):
    """
    Common configurations
    """
    API_VERSION = 1
    APPLICATION_ROOT = '/v{}'.format(API_VERSION)


class DevelopmentConfig(Config):
    """
    Development configurations
    """
    TESTING = True
    DEBUG = True
    SQLALCHEMY_ECHO = True
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    SESSION_TIMEOUT_IN_MINUTES = 120


class ProductionConfig(Config):
    """
    Production configurations
    """
    TESTING = False
    DEBUG = False
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_TIMEOUT_IN_MINUTES = 120

app_config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig
}