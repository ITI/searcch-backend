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
    MAIL_SERVER = "searcch-backend-postfix"
    EMAIL_INTERVAL_DAYS = 30
    MAX_INVITATION_ATTEMPTS = 3

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
    MAIL_SERVER = "searcch-backend-postfix"
    EMAIL_INTERVAL_DAYS = 30
    MAX_INVITATION_ATTEMPTS = 3

app_config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig
}
