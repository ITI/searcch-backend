import sys
import logging
from app.antapi import APP

logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)

application = APP
