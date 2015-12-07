import os
import unittest

from config import basedir
from app import app, db
from app.models import Story, Project, Defect

class TestCase(unittest.TestCase):
  def setUp(self):
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://username:password@localhost/aqusa_test"
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
    assert len(s.defects.all()) == 0

  def test_ends_one_comma(self):
    p = create_project()
    story = Story.create(text="As a User, I want to add a user story so that I document a requirement", project_id=p.id)
    p.analyze()
    defect = story.defects.all()[0]
    assert defect.kind == 'well_formed'
    assert defect.subkind == 'ends_one_comma'
    assert defect.severity == 'medium'
    assert defect.highlight == "As a User, I want to add a user story<span class='highlight-text'>,</span> so that I document a requirement"

  def test_no_comma(self):
    p = create_project()
    story = Story.create(text="As a User I want to add a user story so that I document a requirement", project_id=p.id)
    p.analyze()
    defect = story.defects.all()[0]
    assert defect.kind == 'well_formed'
    assert defect.subkind == 'no_comma'
    assert defect.severity == 'medium'
    assert defect.highlight == "As a User<span class='highlight-text'>,</span> I want to add a user story"

  def test_no_means(self):
    p = create_project()
    story = Story.create(text="As a User, I add a user story, so that I document a requirement", project_id=p.id)
    p.analyze()
    defect = story.defects.filter(Defect.subkind=='no_means')[0]
    assert defect.kind == 'well_formed'
    assert defect.subkind == 'no_means'
    assert defect.severity == 'high'
    assert defect.highlight == "Add a means"

  def test_no_role(self):
    p = create_project()
    story = Story.create(text="User wants to add a user story, so that I document a requirement", project_id=p.id)
    p.analyze()
    defect = story.defects.filter(Defect.subkind=='no_role')[0]
    assert defect.kind == 'well_formed'
    assert defect.subkind == 'no_role'
    assert defect.severity == 'high'
    assert defect.highlight == "Add a role"

class AtomicTests(TestCase):
  def test_not_atomic(self):
    p = create_project()
    story = Story.create(text="As a User, I want to add a user story, so that I document a requirement and sell the system", project_id=p.id)
    p.analyze()
    defect = story.defects.filter(Defect.subkind=='conjunctions')[0]
    assert defect.kind == 'atomic'
    assert defect.subkind == 'conjunctions'
    assert defect.severity == 'high'

class UniqueTests(TestCase):
  def test_identical(self):
    p = create_project()
    story = Story.create(text="As a User, I want to add a user story, so that I document a requirement and sell the system", project_id=p.id)
    story2 = Story.create(text="As a User, I want to add a user story, so that I document a requirement and sell the system", project_id=p.id)
    p.analyze()
    defect1 = story.defects.filter(Defect.subkind=='identical')[0]
    defect2 = story2.defects.filter(Defect.subkind=='identical')[0]
    assert defect1.kind == defect2.kind == 'unique'
    assert defect1.subkind == defect2.subkind == 'identical'
    assert defect1.severity == defect2.severity == 'high'


class MinimalTests(TestCase):
  def test_punctuation(self):
    p = create_project()
    story = Story.create(text="As a User, I want to add a user story, so that I document a requirement and sell the system. This is extra info", project_id=p.id)
    p.analyze()
    defect = story.defects.filter(Defect.subkind=='punctuation')[0]
    assert defect.kind == 'minimal'
    assert defect.subkind == 'punctuation'
    assert defect.severity == 'high'


  def test_brackets(self):
    p = create_project()
    story = Story.create(text="As a User, I want to add a user story, so that I document a requirement and sell the system (for money)", project_id=p.id)
    p.analyze()
    defect = story.defects.filter(Defect.subkind=='brackets')[0]
    assert defect.kind == 'minimal'
    assert defect.subkind == 'brackets'
    assert defect.severity == 'medium'

class UniformTests(TestCase):
  def test_uniformity(self):
    p = create_project()
    Story.create(text="As a User, I want to add a user story, so that I document a requirement", project_id=p.id)
    Story.create(text="As a User, I want to add a user story, so that I document another requirement", project_id=p.id)
    story = Story.create(text="As a User, I am able to add a user story, so that I register a requirement", project_id=p.id)
    p.analyze()
    defect = story.defects.filter(Defect.subkind=='uniform')[0]
    assert defect.kind == 'uniform'
    assert defect.severity == 'medium'


def create_project():
  p = Project.create(name="Test Project")
  return p

def create_story(project_id):
  s = Story.create(text="As a User, I want to add a user story, so that I document a requirement", project_id=project_id)
  return s

