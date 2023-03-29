from env.searcch-backend-local-dev-config import MAX_INVITATION_ATTEMPTS


TESTING = False
DEBUG = False
SQLALCHEMY_ECHO = True
SQLALCHEMY_TRACK_MODIFICATIONS = True
#SESSION_TIMEOUT_IN_MINUTES = 60
SESSION_TIMEOUT_IN_MINUTES = 24*60
SQLALCHEMY_DATABASE_URI = "postgresql+psycopg2cffi://psql_user:psql_password@searcch-backend-prod-postgres:5432/searcchhub"
SHARED_SECRET_KEY = 'shared_secret_key'
DB_AUTO_MIGRATE = True
FRONTEND_URL='https://hub.cyberexperimentation.org'
ADMIN_MAILING_RECIPIENTS = ['searcch-hub@cyberexperimentation.org']
MAIL_DEFAULT_SENDER = 'searcch-hub@cyberexperimentation.org'
MAIL_SERVER = "searcch-backend-postfix"
EMAIL_INTERVAL_DAYS = 30
MAX_INVITATION_ATTEMPTS = 3
