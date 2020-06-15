from flask import Flask, request, jsonify
# from flask_cors import CORS
from flask_pymongo import PyMongo
import json
from bson import json_util

app = Flask(__name__, instance_relative_config=True)
# CORS(app)
app.config.from_object('config')
app.config.from_pyfile('config.py')

mongo = PyMongo(app)

@app.route('/', methods=['GET'])
def index():
    msg = """
        <p> Use the below API endpoints:</p>
        <ul>
            <li><code>/search?keywords="KEYWORDS"</code>  - to get artifacts based on keywords</li>
            <li><code>/record?doi="DOI"</code> - to get data for a specific artifact</li>
        </ul>
    """
    return msg, 200

@app.route('/search', methods=['GET'])
def search_with_keywords():
    """
    searches by text match MongoDB based on keywords

    Returns
    -------
    JSON
        {
            "length": <NUMBER OF RETURNED ARTIFACTS>
            "artifacts": [
                {
                    "doi": <DOI>,
                    "title": <TITLE>,
                    "description": <DESCRIPTION>
                }
            ],
        }
    """
    if "keywords" not in request.args:
        return 'keyword(s) are missing!', 400
    
    kwrds = request.args.get('keywords')
    if kwrds == "":
        docs = mongo.db.relevant_artifacts.find({}).limit(20)
    else:
        docs = mongo.db.relevant_artifacts.find({"$text":{"$search": kwrds}})
    
    artifacts = []
    for doc in docs:
        result = {
            "doi": doc["doi"],
            "title": doc["title"],
            "description": doc["description"],
            "relevance_score": doc["relevance_score"],
            "normalized_relevance_score": doc["normalized_relevance_score"]
        }
        artifacts.append(result)
    
    response = jsonify({"artifacts": artifacts, "length": len(artifacts)})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response, 200

@app.route('/record', methods=['GET'])
def get_record_by_doi():
    """get_record_by_doi returns specific artifact by DOI

    Parameters
    ----------
    doi : String
        unique DOI string for each artifact
    
    Returns
    -------
    JSON
        document from MongoDB
    """
    if "doi" not in request.args:
        return 'DOI is missing!', 404
    
    record = mongo.db.relevant_artifacts.find_one({"doi": request.args.get('doi')})
    if record:
        response = json.loads(json.dumps(record,default=json_util.default))
        response = jsonify(response)
        response.headers.add('Access-Control-Allow-Origin', '*')
        return response, 200
    else:
        return "No document found!", 404

if __name__ == '__main__':    
    app.run()
