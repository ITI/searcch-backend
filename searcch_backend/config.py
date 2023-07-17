class Config(object):
    """
    Common configurations
    """
    API_VERSION = 1
    APPLICATION_ROOT = '/v{}'.format(API_VERSION)
    # Run garbage collector once every day to move data from recent_views table to stats_views table
    STATS_GARBAGE_COLLECTOR_INTERVAL = 24*60*60


class DevelopmentConfig(Config):
    """
    Development configurations
    """
    TESTING = True
    DEBUG = True
    SQLALCHEMY_ECHO = True
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    SESSION_TIMEOUT_IN_MINUTES = 120
    DB_AUTO_MIGRATE = True
    JSON_SORT_KEYS = False
    MAIL_SUPPRESS_SEND = False
    ADMIN_MAILING_RECIPIENTS = []
    MAIL_SERVER = "ant.isi.edu"
    MAIL_PORT = 25
    MAIL_USE_TLS = False

class ProductionConfig(Config):
    """
    Production configurations
    """
    TESTING = False
    DEBUG = False
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_TIMEOUT_IN_MINUTES = 120
    DB_AUTO_MIGRATE = True
    JSON_SORT_KEYS = False
    MAIL_SUPPRESS_SEND = False
    ADMIN_MAILING_RECIPIENTS = []
    MAIL_SERVER = "ant.isi.edu"
    MAIL_PORT = 25
    MAIL_USE_TLS = False

app_config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig
}
