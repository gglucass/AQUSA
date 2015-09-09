from flask import jsonify, abort, session, render_template, request, flash, redirect, url_for, g
from werkzeug import secure_filename
import os
from app import app, babel
from .models import Story, Project, Error, Integration, Webhook
from config import LANGUAGES
import json

@app.route('/')
def index():
  projects = Project.query.all()
  return render_template('index.html', title='Home', projects=projects)

def allowed_file(filename):
  return '.' in filename and \
    filename.rsplit('.', 1)[1] in ['csv']

@app.route('/project/<string:project_unique>/upload_file', methods=['GET', 'POST'])
def upload_file(project_unique):
  project = Project.query.get(project_unique)
  if request.method == 'POST':
    file = request.files['file']
    print(file.filename)
    if file and allowed_file(file.filename):
      filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
      file.save(filepath)
      for story in project.stories.order_by('id').all():
        story.delete()
      project.process_csv(filepath)
      return redirect(url_for('project', project_unique=project_unique))
  return render_template('upload_file.html', title='Upload File', project=project)

@app.route('/projects/new', methods=['GET', 'POST'])
def new_project():
  if request.method == 'POST':
    project = Project.create(request.form['name'])
    return redirect(url_for('project', project_unique=project.id))
  return render_template('new_project.html', title='New Project')


@app.route('/report', methods=['GET'])
def error_report():
  stories = Story.query.order_by('id').all()
  return render_template('report.html', title='Error report', stories=stories)

@app.route('/project/<string:project_unique>', methods=['GET'])
def project(project_unique):
  project = Project.query.get(project_unique)
  project_errors = project.errors.filter_by(false_positive=False).all()
  severe_errors = project.errors.filter_by(severity="high", false_positive=False).all()
  medium_errors = project.errors.filter_by(severity="medium", false_positive=False).all()
  minor_errors = project.errors.filter_by(severity="minor", false_positive=False).all()
  false_positives = project.errors.filter_by(false_positive=True).all()
  perfect_stories = project.stories.filter(Story.errors == None).all()
  stories = project.stories.order_by('id').all()

  return render_template('report.html', title=project.name, project=project, 
    stories=stories, severe_errors=severe_errors, medium_errors=medium_errors, minor_errors=minor_errors, 
    false_positives=false_positives, perfect_stories=perfect_stories, project_errors=project_errors)

@app.route('/project/<string:project_unique>/error/<int:error_id>', methods=['POST'])
def update_error(project_unique, error_id):
  project = Project.query.get(project_unique)
  error = project.errors.filter_by(id=error_id).first()
  if request.form.get('false_positive', None) == 'True':
    error.false_positive = request.form['false_positive']
    error.save()
  if request.form.get('correct_minor_issue', None) == 'True':
    error.correct_minor_issue()
    error.story.re_chunk()
    error.story.re_analyze()
  return redirect(url_for('project', project_unique=project.id))

@app.route('/project/<string:project_unique>/stories/update_story', methods=['POST'])
def update_story(project_unique):
  project = Project.query.get(project_unique)
  story = project.stories.filter_by(id=request.form['id'])[0]
  story.text = request.form['value']
  story.save()
  story.re_chunk()
  story.re_analyze()
  return story.text

@app.route('/project/<string:project_unique>/correct_minor_issues', methods=['POST'])
def correct_minor_issues(project_unique):
  project = Project.query.get(project_unique)
  for error in project.errors.filter_by(severity='minor').all():
    error.correct_minor_issue()
  project.analyze()
  return redirect(url_for('project', project_unique=project.id))

@app.route('/webhook', methods=['POST'])
def webhook():
  data = json.loads(request.data.decode())
  result = Webhook.parse(data)
  return result

@app.route('/submit_project', methods=['GET', 'POST'])
def gp_submit_project():
  if request.method == 'POST':
    kind = request.form['kind']
    integration_project_id = request.form['project_id']
    project = Project.create(request.form['name'])
    api_token = os.environ['GP_API_TOKEN']
    integration = Integration.create(kind, api_token, project, integration_project_id)
    if integration:
      return 'OK'
    else:
      return 400
  return render_template('submit_project.html', title='Submit Project')  
# @app.route('/backend/api/v1.0/stories', methods=['POST'])
# def create_story():
#   if not request.json or not 'text' in request.json or not 'project' in request.json:
#     abort(400)
#   story = Story.create(request.json['text'], request.json['project'])
#   if story.id:
#     return jsonify({'story': story.serialize()}), 201
#   else:
#     abort(400)

# @app.route('/backend/api/v1.0/projects', methods=['POST'])
# def create_project():
#   if not request.json or not 'name' in request.json:
#     abort(400)
#   project = Project.create(request.json['name'])
#   if project.id:
#     return jsonify({'project': project.serialize()}), 201
#   else:
#     abort(400)