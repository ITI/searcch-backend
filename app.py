from configparser import ConfigParser
from flask import Flask, request
import json
import os
import pymongo

app = Flask(__name__)

def connect_to_db():
    config = ConfigParser()
    config.read(os.path.join(os.getcwd(), 'secrets/secrets.ini'))

    DB_USER = config['MONGODB']['CKIDS_USER']
    DB_PASS = config['MONGODB']['CKIDS_PASS']
    DB_NAME = config['MONGODB']['CKIDS_DB_NAME']
    HOST = config['AWS']['HOST_IP']
    PORT = config['AWS']['HOST_PORT']

    # establish connection
    client = pymongo.MongoClient("mongodb://{DB_USER}:{DB_PASS}@{HOST}:{PORT}/{DB_NAME}".format(
        DB_USER=DB_USER, DB_PASS=DB_PASS, HOST=HOST, PORT=PORT, DB_NAME=DB_NAME))
    return client[DB_NAME]

@app.route('/search', methods=['GET'])
def search_with_keywords():
    """
    searches by text match MongoDB based on keywords

    Returns
    -------
    JSON
        {
            "url": [list of URLs for matched Zenodo artifacts]
        }
    """
    if "keywords" not in request.args:
        return 'keywords missing!', 400
    
    kwrds = request.args.get('keywords')
    if kwrds == "":
        db["raw_artifacts"].find({"tfidf_score": {"$gt": 13}}).limit(20)
    else:
        docs = db["raw_artifacts"].find({"$text":{"$search": kwrds}, "tfidf_score": {"$gt": 13}})
    res = ["https://doi.org/" + doc["doi"] for doc in docs]
    return {"url": res}, 200

db = connect_to_db()

if __name__ == '__main__':
    app.run(debug=True)
