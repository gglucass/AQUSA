import os
import unittest

from config import basedir
from app import app, db
from app.models import Story, Project, Error

class TestCase(unittest.TestCase):
  def setUp(self):
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://Garm:myrddin@localhost/aqusa_test"
    self.app = app.test_client()
    db.create_all()

  def tearDown(self):
    db.session.remove()
    db.drop_all()

class ChunkTests(TestCase):
  def test_role_means_ends_chunks(self):
    p = create_project()
    s = Story.create(text="As a User, I want to add a user story, so that I document a requirement", project_id=p.id)
    assert s.role == "As a User,"
    assert s.means == "I want to add a user story,"
    assert s.ends == "so that I document a requirement"

class StoryTests(TestCase):
  def test_create_story(self):
    p = create_project()
    s = create_story(project_id=p.id)
    assert len(Story.query.all()) == 1

  
class WellFormednessTests(TestCase):
  def test_well_formed(self):
    p = create_project()
    s = Story.create(text="As a User, I'm able to add a user story, so that I document a requirement", project_id=p.id)
    s.analyze()
    assert len(s.errors.all()) == 0

  def test_ends_one_comma(self):
    p = create_project()
    story = Story.create(text="As a User, I want to add a user story so that I document a requirement", project_id=p.id)
    p.analyze()
    error = story.errors.all()[0]
    assert error.kind == 'well_formed'
    assert error.subkind == 'ends_one_comma'
    assert error.severity == 'medium'
    assert error.highlight == "As a User, I want to add a user story<span class='highlight-text'>,</span> so that I document a requirement"

  def test_no_comma(self):
    p = create_project()
    story = Story.create(text="As a User I want to add a user story so that I document a requirement", project_id=p.id)
    p.analyze()
    error = story.errors.all()[0]
    assert error.kind == 'well_formed'
    assert error.subkind == 'no_comma'
    assert error.severity == 'medium'
    assert error.highlight == "As a User<span class='highlight-text'>,</span> I want to add a user story"

  def test_no_means(self):
    p = create_project()
    story = Story.create(text="As a User, I add a user story, so that I document a requirement", project_id=p.id)
    p.analyze()
    error = story.errors.filter(Error.subkind=='no_means')[0]
    assert error.kind == 'well_formed'
    assert error.subkind == 'no_means'
    assert error.severity == 'high'
    assert error.highlight == "Add a means"

  def test_no_role(self):
    p = create_project()
    story = Story.create(text="User wants to add a user story, so that I document a requirement", project_id=p.id)
    p.analyze()
    error = story.errors.filter(Error.subkind=='no_role')[0]
    assert error.kind == 'well_formed'
    assert error.subkind == 'no_role'
    assert error.severity == 'high'
    assert error.highlight == "Add a role"

class AtomicTests(TestCase):
  def test_not_atomic(self):
    p = create_project()
    story = Story.create(text="As a User, I want to add a user story, so that I document a requirement and sell the system", project_id=p.id)
    p.analyze()
    error = story.errors.filter(Error.subkind=='conjunctions')[0]
    assert error.kind == 'atomic'
    assert error.subkind == 'conjunctions'
    assert error.severity == 'high'

class UniqueTests(TestCase):
  def test_identical(self):
    p = create_project()
    story = Story.create(text="As a User, I want to add a user story, so that I document a requirement and sell the system", project_id=p.id)
    story2 = Story.create(text="As a User, I want to add a user story, so that I document a requirement and sell the system", project_id=p.id)
    p.analyze()
    error1 = story.errors.filter(Error.subkind=='identical')[0]
    error2 = story2.errors.filter(Error.subkind=='identical')[0]
    assert error1.kind == error2.kind == 'unique'
    assert error1.subkind == error2.subkind == 'identical'
    assert error1.severity == error2.severity == 'high'


class MinimalTests(TestCase):
  def test_punctuation(self):
    p = create_project()
    story = Story.create(text="As a User, I want to add a user story, so that I document a requirement and sell the system. This is extra info", project_id=p.id)
    p.analyze()
    error = story.errors.filter(Error.subkind=='punctuation')[0]
    assert error.kind == 'minimal'
    assert error.subkind == 'punctuation'
    assert error.severity == 'high'


  def test_brackets(self):
    p = create_project()
    story = Story.create(text="As a User, I want to add a user story, so that I document a requirement and sell the system (for money)", project_id=p.id)
    p.analyze()
    error = story.errors.filter(Error.subkind=='brackets')[0]
    assert error.kind == 'minimal'
    assert error.subkind == 'brackets'
    assert error.severity == 'medium'

class UniformTests(TestCase):
  def test_uniformity(self):
    p = create_project()
    Story.create(text="As a User, I want to add a user story, so that I document a requirement", project_id=p.id)
    Story.create(text="As a User, I want to add a user story, so that I document another requirement", project_id=p.id)
    story = Story.create(text="As a User, I am able to add a user story, so that I register a requirement", project_id=p.id)
    p.analyze()
    error = story.errors.filter(Error.subkind=='uniform')[0]
    assert error.kind == 'uniform'
    assert error.severity == 'medium'


def create_project():
  p = Project.create(name="Test Project")
  return p

def create_story(project_id):
  s = Story.create(text="As a User, I want to add a user story, so that I document a requirement", project_id=project_id)
  return s

