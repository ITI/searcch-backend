from app import app
from flask import request, jsonify, render_template
from flask_pymongo import PyMongo
import json
from bson import json_util

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# @app.route('/search', methods=['GET'])
# def search_with_keywords():
#     """
#     searches by text match MongoDB based on keywords

#     Returns
#     -------
#     JSON
#         {
#             "length": <NUMBER OF RETURNED ARTIFACTS>
#             "artifacts": [
#                 {
#                     "doi": <DOI>,
#                     "title": <TITLE>,
#                     "description": <DESCRIPTION>
#                 }
#             ],
#         }
#     """
#     if "keywords" not in request.args:
#         return 'keyword(s) are missing!', 400
    
#     kwrds = request.args.get('keywords')
#     if kwrds == "":
#         docs = mongo.db.relevant_artifacts.find({}).sort([('relevance_score', -1)]).limit(20)
#     else:
#         # docs = mongo.db.relevant_artifacts.find({"$text":{"$search": kwrds}})
#         docs = mongo.db.relevant_artifacts.find(
#             {"$text":{"$search": kwrds}}, 
#             {"score": {"$meta": "textScore"}}
#         ).sort([('score', {'$meta': 'textScore'})])
    
#     artifacts = []
#     for doc in docs:
#         result = {
#             "doi": doc["doi"],
#             "title": doc["title"],
#             "description": doc["description"],
#             "type": doc["resource_type"]["type"], 
#             "relevance_score": round(doc["score"], 3)
#         }
#         artifacts.append(result)
    
#     response = jsonify({"artifacts": artifacts, "length": len(artifacts)})
#     response.headers.add('Access-Control-Allow-Origin', '*')
#     return response, 200

# @app.route('/record', methods=['GET'])
# def get_record_by_doi():
#     """get_record_by_doi returns specific artifact by DOI

#     Parameters
#     ----------
#     doi : String
#         unique DOI string for each artifact
    
#     Returns
#     -------
#     JSON
#         document from MongoDB
#     """
#     if "doi" not in request.args:
#         return 'DOI is missing!', 404
    
#     record = mongo.db.relevant_artifacts.find_one({"doi": request.args.get('doi')})
#     if record:
#         response = json.loads(json.dumps(record,default=json_util.default))
#         response = jsonify(response)
#         response.headers.add('Access-Control-Allow-Origin', '*')
#         return response, 200
#     else:
#         return "No document found!", 404


