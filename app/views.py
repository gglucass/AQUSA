from flask import jsonify, abort, session, render_template, request, flash, redirect, url_for, g
from werkzeug import secure_filename
import os
from app import app, babel
from .models import Stories, Projects, Defects
from config import LANGUAGES
import json
import time

@app.route('/')
def index():
  projects = Projects.query.all()
  return render_template('index.html', title='Home', projects=projects)

def allowed_file(filename):
  return '.' in filename and \
    filename.rsplit('.', 1)[1] in ['csv']

@app.route('/project/<string:project_unique>/upload_file', methods=['GET', 'POST'])
def upload_file(project_unique):
  project = Projects.query.get(project_unique)
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
    project = Projects.create(request.form['name'])
    return redirect(url_for('project', project_unique=project.id))
  return render_template('new_project.html', title='New Project')


@app.route('/report', methods=['GET'])
def defect_report():
  stories = stories.query.order_by('id').all()
  return render_template('report.html', title='Defect report', stories=stories)

@app.route('/project/<string:project_unique>', methods=['GET'])
def project(project_unique):
  project = Projects.query.get(project_unique)
  project_defects = project.defects.filter_by(false_positive=False).all()
  severe_defects = project.defects.filter_by(severity="high", false_positive=False).all()
  medium_defects = project.defects.filter_by(severity="medium", false_positive=False).all()
  minor_defects = project.defects.filter_by(severity="minor", false_positive=False).all()
  false_positives = project.defects.filter_by(false_positive=True).all()
  perfect_stories = project.stories.filter(Stories.defects == None).all()
  stories = project.stories.order_by('id').all()

  return render_template('report.html', title=project.name, project=project, 
    stories=stories, severe_defects=severe_defects, medium_defects=medium_defects, minor_defects=minor_defects, 
    false_positives=false_positives, perfect_stories=perfect_stories, project_defects=project_defects)

@app.route('/project/<string:project_unique>/defect/<int:defect_id>', methods=['POST'])
def update_defect(project_unique, defect_id):
  project = Projects.query.get(project_unique)
  defect = project.defects.filter_by(id=defect_id).first()
  if request.form.get('false_positive', None) == 'True':
    defect.false_positive = request.form['false_positive']
    defect.save()
  if request.form.get('correct_minor_issue', None) == 'True':
    defect.correct_minor_issue()
    defect.story.re_chunk()
    defect.story.re_analyze()
  return redirect(url_for('project', project_unique=project.id))

@app.route('/project/<string:project_unique>/stories/update_story', methods=['POST'])
def update_story(project_unique):
  project = Projects.query.get(project_unique)
  story = project.stories.filter_by(id=request.form['id'])[0]
  story.title = request.form['value']
  story.save()
  story.re_chunk()
  story.re_analyze()
  return story.title

@app.route('/project/<string:project_unique>/correct_minor_issues', methods=['POST'])
def correct_minor_issues(project_unique):
  project = Projects.query.get(project_unique)
  for defect in project.defects.filter_by(severity='minor').all():
    defect.correct_minor_issue()
  project.analyze()
  return redirect(url_for('project', project_unique=project.id))

@app.route('/project/<string:project_unique>/analyze', methods=['GET'])
def analyze_project(project_unique):
  project = Projects.query.get(project_unique)
  if project == None: time.sleep(2)
  project.analyze()

  return jsonify({'success': True}), 200

@app.route('/project/<string:project_unique>/stories/<string:story_unique>/analyze', methods=['GET'])
def analyze_story(project_unique, story_unique):
  project = Projects.query.get(project_unique)
  if project == None: time.sleep(2)
  story = project.stories.filter_by(id=story_unique).first()
  story.re_chunk()
  story.analyze()
  return jsonify({'success': True}), 200


# @app.route('/backend/api/v1.0/stories', methods=['POST'])
# def create_story():
#   if not request.json or not 'text' in request.json or not 'project' in request.json:
#     abort(400)
#   story = stories.create(request.json['text'], request.json['project'])
#   if story.id:
#     return jsonify({'story': story.serialize()}), 201
#   else:
#     abort(400)

# @app.route('/backend/api/v1.0/projects', methods=['POST'])
# def create_project():
#   if not request.json or not 'name' in request.json:
#     abort(400)
#   project = Projects.create(request.json['name'])
#   if project.id:
#     return jsonify({'project': project.serialize()}), 201
#   else:
#     abort(400)