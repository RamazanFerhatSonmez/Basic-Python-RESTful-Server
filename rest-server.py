#!flask/bin/python
from flask import Flask, jsonify, json, abort, request, make_response, url_for, Response
#from flask.ext.httpauth import HTTPBasicAuth
from luminoso_api import LuminosoClient
from luminoso_api.errors import LuminosoError, LuminosoClientError
from luminoso_api.json_stream import open_json_or_csv_somehow
from werkzeug.datastructures import ImmutableMultiDict

import logging, urlparse

app = Flask(__name__, static_url_path = "")
#auth = HTTPBasicAuth()
file_handler = logging.FileHandler('app.log')
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

@app.errorhandler(400)
def not_found(error):
    app.logger.error('Bad Request - 400')
    return make_response(jsonify( { 'error': 'Bad request' } ), 400)
 
@app.errorhandler(404)
def not_found(error):
    app.logger.error('Not found - 404')
    return make_response(jsonify( { 'error': 'Not found' } ), 404)

@app.route('/api/v1.0/test', methods = ['GET'])
def get_test():

    data = {
        'hello'  : 'world',
        'number' : 3
    }
    
    js = json.dumps(data)
    
    app.logger.info('Echo:' + js)

    resp = Response(js, status=200, mimetype='application/json')
    resp.headers['Link'] = 'http://localhost'

    return resp
#    return "ECHO: GET\n"

@app.route('/api/v1.0/test', methods = ['POST'])
def post_test():
    if request.headers['Content-Type'] == 'text/plain':
        app.logger.info('Echo:' + request.data)
        return "Text Message: " + request.data
    
    elif request.headers['Content-Type'] == 'application/json':
        app.logger.info('Echo:' + json.dumps(request.json))
        return "JSON Message: " + json.dumps(request.json)

    elif request.headers['Content-Type'] == 'application/octet-stream':
        f = open('./binary', 'wb')
        f.write(request.data)
        f.close()
        app.logger.info('Echo:' + request.data)
        return "Binary message written!"
    else:
        app.logger.info('Echo: 415 Unsupported Media Type')
        return "415 Unsupported Media Type ;)"
#    return "ECHO: GET\n"
#
#   Get list of projects
#
@app.route('/api/v1.0/get_projects', methods = ['GET'])
def get_luminoso():
    app.logger.info('Get from luminoso')
    
    client = LuminosoClient.connect(request.args.get('luminoso_account'),
                                    username=request.args.get('luminoso_account_name'), 
                                    password=request.args.get('luminoso_password'))
    project_info_list = client.get()
    
    return json.dumps(project_info_list)
#
#  Create Projects
#
@app.route('/api/v1.0/create_projects', methods = ['GET','POST'])
def get_luminosocreate():
    
    app.logger.info('Create a project on Luminoso')
    
    client = LuminosoClient.connect(request.args.get('luminoso_account'),
                                    username=request.args.get('luminoso_account_name'), 
                                    password=request.args.get('luminoso_password'))
    # Create a new project by POSTing its name
    project_id = client.post(name=request.args.get('project_name'))['project_id']
    # use that project from here on
    project = client.change_path(project_id)
    return 'true'
#
# Upload documents
#
@app.route('/api/v1.0/update_docs', methods = ['GET','POST'])
def get_update_docs():
    
    app.logger.info('Upload documents Luminoso')
    
    client = LuminosoClient.connect(request.args.get('luminoso_account'),
                                    username=request.args.get('luminoso_account_name'), 
                                    password=request.args.get('luminoso_password'))
    # Create a new project by POSTing its name
    project = client.get(name=request.args.get('project_name'))[0]
    project = client.change_path(project['project_id'])

    try:
        json_object = json.loads(request.args.get('project_doc'))
    except ValueError, e:
        return False
#    raise Exception(request.args.get('project_doc'))
    
    project.upload('docs/preload', json.loads(request.args.get('project_doc')))
    job_id = project.post('docs/recalculate')
    
    project.wait_for(job_id)
    
    response = project.get('terms')
    terms = [(term['text'], term['score']) for term in response]

    return json.dumps(terms)

#
#  Delete project
#
@app.route('/api/v1.0/delete_project', methods = ['GET'])
def get_luminosodelete():
    app.logger.info('Delete a project on Luminoso')
    client = LuminosoClient.connect(request.args.get('luminoso_account'),
                                    username=request.args.get('luminoso_account_name'), 
                                    password=request.args.get('luminoso_password'))
   # Delete new project by POSTing its name
    projects.delete(request.args.get('project_id'))
    
    return "Project Deleted "
#
#  Get correlation
#
@app.route('/api/v1.0/get_correlation', methods = ['GET','POST'])
def get_correlation():
    
    app.logger.info('Get Correlation')
    
    client = LuminosoClient.connect(request.args.get('luminoso_account'),
                                    username=request.args.get('luminoso_account_name'), 
                                    password=request.args.get('luminoso_password'))
    
    project = client.get(name=request.args.get('project_name'))[0]
    project = client.change_path(project['project_id'])
    
    # get list of topics
    topics = project.get('topics/')
    result = project.put('topics/text_correlation', text=request.args.get('article_text'))

    correlations = []
    for key, value in result.iteritems():
        correlations.append([(t['name'], value) for t in topics if t['_id']==key])

    return json.dumps(correlations) 
#
#   Set Topics Data
#
@app.route('/api/v1.0/post_set_topics', methods = ['GET'])
def post_set_topics():
    
    # In[1]:
    app.logger.info('Echo:' + json.dumps(request.json))
    # see API documentation: https://api.luminoso.com/v4/
    # use account # and username provisioned
    project_name = "GP english sample"
    client = LuminosoClient.connect(request.args.get('luminoso_account'),
                                    username=request.args.get('luminoso_account_name'), 
                                    password=request.args.get('luminoso_password'))
    # Get project id from project name:
    project = client.get(name=project_name)[0]
    project = client.change_path(project['project_id'])
    # delete and then recreate topics
    topics = project.get('topics/')
    for topic in topics:
        project.delete('topics/id/'+topic['_id'])
        new_topic = project.post('topics/', name="Oceans", text="ocean marine")
        new_topic = project.post('topics/', name="Whales", text="whales")
        new_topic = project.post('topics/', name="Seals", text="seals")
        new_topic = project.post('topics/', name="Japan", text="Japan")
        new_topic = project.post('topics/', name="Overfishing", text="fishing overfishing")
        new_topic = project.post('topics/', name="Forests", text="forests")
        new_topic = project.post('topics/', name="Climate & Energy", text="climate fuel pollution")
        new_topic = project.post('topics/', name="Polar", text="polar ice")
        topics = project.get('topics/')

    return 'true' 
    
if __name__ == '__main__':
    app.run(debug = True)