#!venv/bin/python

'''
standalone run antapi in debug mode
'''

import os

from app.antapi import APP

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    APP.run(host='0.0.0.0', port=port, debug=False)
