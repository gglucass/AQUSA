# -*- coding: utf-8 -*-

from app import db
from .taggers import StanfordTagger
AQUSATagger = StanfordTagger()

import re
import nltk
import pandas
import operator
import pycurl
import json
import threading
from flask.ext.babel import Babel, gettext
from io import BytesIO
from collections import Counter
import sqlalchemy as sa
from sqlalchemy_continuum import make_versioned
make_versioned(user_cls=None)

# Classes: Story, Error, Project  

class Story(db.Model):
  __versioned__ = {}
  __tablename__ = 'story'
  id = db.Column(db.Integer, primary_key=True)
  external_id = db.Column(db.String(120))
  text = db.Column(db.Text)
  role = db.Column(db.Text)
  means = db.Column(db.Text)
  ends = db.Column(db.Text)
  project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
  errors = db.relationship('Error', backref='story', lazy='dynamic', cascade='save-update, merge, delete')

  def __repr__(self):
    return '<story: %r, text=%s>' % (self.id, self.text)

  def serialize(self):
    class_dict = self.__dict__
    del class_dict['_sa_instance_state']
    return class_dict

  def create(text, project_id, external_id, analyze=False):
    story = Story(text=text, project_id=project_id, external_id=external_id)
    db.session.add(story)
    db.session.commit()
    db.session.merge(story)
    story.chunk()
    if analyze: story.analyze()
    return story

  def save(self):
    db.session.add(self)
    db.session.commit()
    db.session.merge(self)
    return self

  def delete(self):
    db.session.delete(self)
    db.session.commit()

  def chunk(self):
    StoryChunker.chunk_story(self)
    return self

  def re_chunk(self):
    self.role = None
    self.means = None
    self.ends = None
    StoryChunker.chunk_story(self)
    return self

  def analyze(self):
    WellFormedAnalyzer.well_formed(self)
    Analyzer.atomic(self)
    Analyzer.unique(self, True)
    MinimalAnalyzer.minimal(self)
    Analyzer.uniform(self)
    self.remove_duplicates_of_false_positives()
    return self

  def re_analyze(self):
    for error in Error.query.filter_by(story=self, false_positive=False).all():
      for comment in error.comments.all():
        integration = comment.error.project.integration.first()
        threading.Thread(target=Comment.post_delete_to_pivotal, args=(comment.external_id, comment.error.story.external_id, integration.integration_project_id, integration.api_token)).start()
      error.delete()
    self.analyze()
    return self

  def remove_duplicates_of_false_positives(self):
    for false_positive in self.errors.filter_by(false_positive=True):
      duplicates = Error.query.filter_by(story=self, kind=false_positive.kind, subkind=false_positive.subkind, false_positive=False).all()
      if duplicates:
        for duplicate in duplicates:
          duplicate.delete()
      else:
        false_positive.delete()
    return self

class Integration(db.Model):
  __versioned__ = {}
  __tablename__ = 'integration'
  id = db.Column(db.Integer, primary_key=True)
  kind = db.Column(db.String(120), nullable=False)
  api_token = db.Column(db.String(250), nullable=False)
  project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
  integration_project_id = db.Column(db.String(250), nullable=False)

  def __repr__(self):
    return '<Integration: %r, kind=%r, project=%r>' % (self.id, self.kind, self.project.name)

  def create(kind, api_token, project, integration_project_id):
    integration = Integration(kind=kind, api_token=api_token, project_id=project.id, integration_project_id=integration_project_id)
    db.session.add(integration)
    db.session.commit()
    db.session.merge(integration)
    return integration

  def delete(self):
    db.session.delete(self)
    db.session.commit() 

  def save(self):
    db.session.add(self)
    db.session.commit()
    db.session.merge(self)
    return self


class Project(db.Model):
  __versioned__ = {}
  __tablename__ = 'project'
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(120), index=True, nullable=False)
  format = db.Column(db.Text, nullable=True, default="As a,I want to,So that")
  stories = db.relationship('Story', backref='project', lazy='dynamic', cascade='save-update, merge, delete')
  errors = db.relationship('Error', backref='project', lazy='dynamic')
  integration = db.relationship('Integration', backref='project', lazy='dynamic', cascade='save-update, merge, delete')

  def __repr__(self):
    return '<Project: %r, name=%s>' % (self.id, self.name)

  def serialize(self):
    class_dict = self.__dict__
    del class_dict['_sa_instance_state']
    return class_dict

  def create(name):
    project = Project(name=name)
    db.session.add(project)
    db.session.commit()
    db.session.merge(project)
    return project

  def delete(self):
    db.session.delete(self)
    db.session.commit() 

  def save(self):
    db.session.add(self)
    db.session.commit()
    db.session.merge(self)
    return self

  def process_csv(self, path):
    stories = pandas.read_csv(path, header=-1)
    for story in stories[0]: 
      Story.create(text=story, project_id=self.id)
    self.analyze()
    return None

  def get_common_format(self):
    most_common_format = []
    for chunk in ['role', 'means', 'ends']:
      chunks = [Analyzer.extract_indicator_phrases(getattr(story,chunk), chunk) for story in self.stories]
      chunks = list(filter(None, chunks))
      try:
        most_common_format += [Counter(chunks).most_common(1)[0][0].strip()]
      except:
        print('')
    self.format = ', '.join(most_common_format)
    self.save()
    return "New format is: " + self.format

  def analyze(self):
    self.get_common_format()
    for story in self.stories.all():
      story.re_chunk()
      story.re_analyze()
    return self

class Error(db.Model):
  __versioned__ = {}
  __tablename__ = 'error'
  id = db.Column(db.Integer, primary_key=True)
  highlight = db.Column(db.Text, nullable=False)
  kind = db.Column(db.String(120), index=True,  nullable=False)
  subkind = db.Column(db.String(120), nullable=False)
  severity = db.Column(db.String(120), nullable=False)
  false_positive = db.Column(db.Boolean, default=False, nullable=False)
  comments = db.relationship('Comment', backref='error', lazy='dynamic', cascade='save-update, merge, delete')
  story_id = db.Column(db.Integer, db.ForeignKey('story.id'), nullable=False)
  project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)

  def __repr__(self):
    return '<Error: %s, highlight=%s, kind=%s>' % (self.id, self.highlight, self.kind)

  def create(highlight, kind, subkind, severity, story):
    error = Error(highlight=highlight, kind=kind, subkind=subkind, severity=severity, story_id=story.id, project_id=story.project.id)
    db.session.add(error)
    db.session.commit()
    db.session.merge(error)
    return error

  def delete(self):
    db.session.delete(self)
    db.session.commit()

  def save(self):
    db.session.add(self)
    db.session.commit()
    db.session.merge(self)
    return self

  def create_unless_duplicate(highlight, kind, subkind, severity, story):
    error = Error(highlight=highlight, kind=kind, subkind=subkind, severity=severity, story_id=story.id, project_id=story.project.id)
    duplicates = Error.query.filter_by(highlight=highlight, kind=kind, subkind=subkind,
      severity=severity, story_id=story.id, project_id=story.project.id, false_positive=False).all()
    if duplicates:
      return 'duplicate'
    else:
      db.session.add(error)
      db.session.commit()
      db.session.merge(error)
      db.session.refresh(error)
      threading.Thread(target=Comment.create, args=(error, story)).start()
      return error

  def correct_minor_issue(self):
    story = self.story
    CorrectError.correct_minor_issue(self)
    return story

ROLE_INDICATORS = ["^As an ", "^As a ", "^As "]
MEANS_INDICATORS = ["I'm able to ", "I am able to ", "I want to ", "I wish to ", "I can "]
ENDS_INDICATORS = ["So that ", "In order to ", "So "]
CONJUNCTIONS = [' and ', '&', '+', ' or ']
PUNCTUATION = ['.', ';', ':', '‒', '–', '—', '―', '‐', '-', '?', '*']
BRACKETS = [['(', ')'], ['[', ']'], ['{', '}'], ['⟨', '⟩']]
ERROR_KINDS = { 'well_formed_content': [
                  { 'subkind': 'means', 'rule': 'Analyzer.well_formed_content_rule(story.means, "means", ["means"])', 'severity':'medium', 'highlight':'str("Make sure the means includes a verb and a noun. Our analysis shows the means currently includes: ") + Analyzer.well_formed_content_highlight(story.means, "means")'},
                  { 'subkind': 'role', 'rule': 'Analyzer.well_formed_content_rule(story.role, "role", ["NP"])', 'severity':'medium', 'highlight':'str("Make sure the role includes a person noun. Our analysis shows the role currently includes: ") + Analyzer.well_formed_content_highlight(story.role, "role")'},
                ],

                'atomic': [
                  { 'subkind':'conjunctions', 'rule':"Analyzer.atomic_rule(getattr(story,chunk), chunk)", 'severity':'high', 'highlight':"Analyzer.highlight_text(story, CONJUNCTIONS, 'high')"}
                ],
                'unique': [
                  { 'subkind':'identical', 'rule':"Analyzer.identical_rule(story, cascade)", 'severity':'high', 'highlight':'str("Remove all duplicate user stories")' }
                ],
                'uniform': [
                  { 'subkind':'uniform', 'rule':"Analyzer.uniform_rule(story)", 'severity':'medium', 'highlight':'"Use the most common template: %s" % story.project.format'}
                ],

              }
CHUNK_GRAMMAR = """
      NP: {<DT|JJ|NN.*>}
      NNP: {<NNP.*>}
      AP: {<RB.*|JJ.*>}
      VP: {<VB.*><NP>*}
      MEANS: {<AP>?<VP>}
      ENDS: {<AP>?<VP>}
    """

class Analyzer:
  def atomic(story):
    for chunk in ['"role"', '"means"', '"ends"']:
      Analyzer.generate_errors('atomic', story, chunk=chunk)
    return story

  def unique(story, cascade):
    Analyzer.generate_errors('unique', story, cascade=cascade)
    return story

  def uniform(story):
    Analyzer.generate_errors('uniform', story)
    return story
      
  def detect_indicator_phrases(text):
    indicator_phrases = {'role': False, 'means': False, 'ends': False}
    for key in indicator_phrases:
      for indicator_phrase in eval(key.upper() + '_INDICATORS'):
        if indicator_phrase.lower() in text.lower(): indicator_phrases[key] = True
    return indicator_phrases

  def generate_errors(kind, story, **kwargs):
    for kwarg in kwargs:
      exec(kwarg+'='+ str(kwargs[kwarg]))
    for error_type in ERROR_KINDS[kind]:
      if eval(error_type['rule']):
        Error.create_unless_duplicate(eval(error_type['highlight']), kind, error_type['subkind'], error_type['severity'], story)

  def inject_text(text, severity='medium'):
    return "<span class='highlight-text severity-" + severity + "'>%s</span>" % text

  def atomic_rule(chunk, kind):
    sentences_invalid = []
    if chunk: 
      for x in CONJUNCTIONS:
        if x in chunk.lower():
          if kind == 'means':
            for means in chunk.split(x):
              sentences_invalid.append(Analyzer.well_formed_content_rule(means, 'means', ['MEANS']))
          if kind == 'role':
            for role in chunk.split(x):
              sentences_invalid.append(Analyzer.well_formed_content_rule(role, "role", ["NP"]))
    return sentences_invalid.count(False) > 1

  def identical_rule(story, cascade):
    identical_stories = Story.query.filter((Story.text==story.text) & (Story.project_id == int(story.project_id))).all()
    identical_stories.remove(story)
    if cascade:
      for story in identical_stories:
        for error in story.errors.filter(Error.kind=='unique').all(): error.delete()
        Analyzer.unique(story, False)
    return (True if identical_stories else False)

  def highlight_text(story, word_array, severity):
    highlighted_text = story.text
    indices = []
    for word in word_array:
      if word in story.text.lower(): indices += [ [story.text.index(word), word] ]
    indices.sort(reverse=True)
    for index, word in indices:
      highlighted_text = highlighted_text[:index] + "<span class='highlight-text severity-" + severity + "'>" + word + "</span>" + highlighted_text[index+len(word):]
    return highlighted_text

  def well_formed_content_rule(story_part, kind, tags):
    result = Analyzer.content_chunk(story_part, kind)
    well_formed = True
    for tag in tags:
      for x in result.subtrees():
        if tag.upper() in x.label(): well_formed = False
    return well_formed

  def uniform_rule(story):
    result = False
    if story.project.stories.count() > 3:
      project_format = story.project.format.split(',')
      chunks = []
      for chunk in ['role', 'means', 'ends']:
        chunks += [Analyzer.extract_indicator_phrases(getattr(story,chunk), chunk)]
      chunks = list(filter(None, chunks))
      chunks = [c.strip() for c in chunks]
      if len(chunks) == 1: result = True
      for x in range(0,len(chunks)):
        if nltk.metrics.distance.edit_distance(chunks[x].lower(), project_format[x].lower()) > 3:
          result = True 
    return result

  def well_formed_content_highlight(story_part, kind):
    return str(Analyzer.content_chunk(story_part, kind))

  def content_chunk(chunk, kind):
    sentence = AQUSATagger.parse(chunk)[0]
    sentence = Analyzer.strip_indicators_pos(chunk, sentence, kind)
    cp = nltk.RegexpParser(CHUNK_GRAMMAR)
    result = cp.parse(sentence)
    return result

  def extract_indicator_phrases(text, indicator_type):
    if text:
      indicator_phrase = []
      for indicator in eval(indicator_type.upper() + '_INDICATORS'):
        if re.compile('(%s)' % indicator.lower()).search(text.lower()): indicator_phrase += [indicator.replace('^', '')]
      return max(indicator_phrase, key=len) if indicator_phrase else None
    else:
      return text

  def strip_indicators_pos(text, pos_text, indicator_type):
    for indicator in eval(indicator_type.upper() + '_INDICATORS'):
      if indicator.lower().strip() in text.lower():
        indicator_words = nltk.word_tokenize(indicator)
        pos_text = [x for x in pos_text if x[0] not in indicator_words]
    return pos_text


class WellFormedAnalyzer:
  def well_formed(story):
    WellFormedAnalyzer.means(story)
    WellFormedAnalyzer.role(story)
    WellFormedAnalyzer.means_comma(story)
    WellFormedAnalyzer.ends_comma(story)
    return story

  def means(story):
    if not story.means:
      Error.create_unless_duplicate('Add a means', 'well_formed', 'no_means', 'high', story )
    return story

  def role(story):
    if not story.role:
      Error.create_unless_duplicate('Add a role', 'well_formed', 'no_role', 'high', story )
    return story

  def means_comma(story):
    if story.role is not None and story.means is not None:
      if story.role.count(',') == 0:
        highlight = story.role + Analyzer.inject_text(',') + ' ' + story.means
        Error.create_unless_duplicate(highlight, 'well_formed', 'no_means_comma', 'minor', story )
    return story

  def ends_comma(story):
    if story.means is not None and story.ends is not None:
      if story.means.count(',') == 0:
        highlight = story.means + Analyzer.inject_text(',') + ' ' + story.ends
        Error.create_unless_duplicate(highlight, 'well_formed', 'no_ends_comma', 'minor', story )
    return story

class MinimalAnalyzer:
  def minimal(story):
    MinimalAnalyzer.punctuation(story)
    MinimalAnalyzer.brackets(story)
    return story

  def punctuation(story):
    if any(re.compile('(\%s .)' % x).search(story.text.lower()) for x in PUNCTUATION):
      highlight = MinimalAnalyzer.punctuation_highlight(story, 'high')
      Error.create_unless_duplicate(highlight, 'minimal', 'punctuation', 'high', story )
    return story

  def punctuation_highlight(story, severity):
    highlighted_text = story.text
    indices = []
    for word in PUNCTUATION:
      if re.search('(\%s .)' % word, story.text.lower()): indices += [ [story.text.index(word), word] ]
    first_punct = min(indices)
    highlighted_text = highlighted_text[:first_punct[0]] + "<span class='highlight-text severity-" + severity + "'>" + highlighted_text[first_punct[0]:] + "</span>"
    return highlighted_text

  def brackets(story):
    if any(re.compile('(\%s' % x[0] + '.*\%s(\W|\Z))' % x[1]).search(story.text.lower()) for x in BRACKETS):
      highlight = MinimalAnalyzer.brackets_highlight(story, 'high')
      Error.create_unless_duplicate(highlight, 'minimal', 'brackets', 'high', story )
    return story.errors.all()

  def brackets_highlight(story, severity):
    highlighted_text = story.text
    matches = []
    for x in BRACKETS:
      split_string = '[^\%s' % x[1] + ']+\%s' % x[1]
      strings = re.findall(split_string, story.text)
      match_string = '(\%s' % x[0] + '.*\%s(\W|\Z))' % x[1]
      string_length = 0
      for string in strings:
        result = re.compile(match_string).search(string.lower())
        if result:
          span = tuple(map(operator.add, result.span(), (string_length, string_length)))
          matches += [ [span, result.group()] ]
        string_length += len(string)
    matches.sort(reverse=True)
    for index, word in matches:
      highlighted_text = highlighted_text[:index[0]] + "<span class='highlight-text severity-" +  severity + "'>" + word + "</span>" + highlighted_text[index[1]:]
    return highlighted_text

class StoryChunker:
  def chunk_story(story):
    StoryChunker.chunk_on_indicators(story)
    if story.means is None:
      potential_means = story.text
      if story.role is not None:
        potential_means = potential_means.replace(story.role, "", 1).strip()
      if story.ends is not None:
        potential_means = potential_means.replace(story.ends, "", 1).strip()
      StoryChunker.means_tags_present(story, potential_means)
    return story.role, story.means, story.ends

  def detect_indicators(story):
    indicators = {'role': None, "means": None, 'ends': None}
    for indicator in indicators:
      indicator_phrase = StoryChunker.detect_indicator_phrase(story.text, indicator)
      if indicator_phrase[0]:
        indicators[indicator.lower()] = story.text.lower().index(indicator_phrase[1].lower())
    return indicators

  def detect_indicator_phrase(text, indicator_type):
    result = False
    detected_indicators = ['']
    for indicator_phrase in eval(indicator_type.upper() + '_INDICATORS'):
      if re.compile('(%s)' % indicator_phrase.lower()).search(text.lower()): 
        result = True
        detected_indicators.append(indicator_phrase.replace('^', ''))
    return (result, max(detected_indicators, key=len))

  def chunk_on_indicators(story):
    indicators = StoryChunker.detect_indicators(story)
    if indicators['means'] is not None and indicators['ends'] is not None:
      indicators = StoryChunker.correct_erroneous_indicators(story, indicators)
    if indicators['role'] is not None and indicators['means'] is not None:
      story.role = story.text[indicators['role']:indicators['means']].strip()
      story.means = story.text[indicators['means']:indicators['ends']].strip()
    elif indicators['role'] is not None and indicators['means'] is None:
      role = StoryChunker.detect_indicator_phrase(story.text, 'role')
      new_text = story.text.replace(role[1], '')
      sentence = Analyzer.content_chunk(new_text, 'role')
      NPs_after_role = StoryChunker.keep_if_NP(sentence)
      if NPs_after_role:
        story.role = story.text[indicators['role']:(len(role[1]) + len(NPs_after_role))].strip()
    if indicators['ends']: story.ends = story.text[indicators['ends']:None].strip()
    story.save()
    return story

  def keep_if_NP(parsed_tree):
    return_string = []
    for leaf in parsed_tree:
      if type(leaf) is not tuple:
        if leaf[0][0] == 'I':
          break
        elif leaf.label() == 'NP': 
          return_string.append(leaf[0][0])
        else:
          break
      elif leaf == (',', ','): return_string.append(',')
    return ' '.join(return_string)

  def means_tags_present(story, string):
    if not Analyzer.well_formed_content_rule(string, 'means', ['MEANS']):
      story.means = string
      story.save
    return story

  def correct_erroneous_indicators(story, indicators):
    # means is larger than ends
    if indicators['means'] > indicators['ends']:
      new_means = StoryChunker.detect_indicator_phrase(story.text[:indicators['ends']], 'means')
      #replication of #427 - refactor?
      if new_means[0]:
        indicators['means'] = story.text.lower().index(new_means[1].lower())
      else:
        indicators['means'] = None
    return indicators


class CorrectError:
  def correct_minor_issue(error):
    story = error.story
    eval('CorrectError.correct_%s(error)' % error.subkind)
    return story

  def correct_no_means_comma(error):
    story = error.story
    story.text = story.role + ', ' + story.means 
    if story.ends: story.text = story.text + ' ' + story.ends
    story.save()
    return story

  def correct_no_ends_comma(error):
    story = error.story
    story.text = story.means + ', ' + story.ends
    if story.role: story.text = story.role + ' ' + story.text
    story.save()
    return story

class Webhook:
  def parse(json_data):
    project = Webhook.get_project(json_data)
    for change in json_data['changes']:
      eval('Webhook.' + change['change_type'] + '(change, project)')
    return "OK"

  def create(change, project):
    values = change['new_values']
    story = Story.create(values['name'], project.id, values['id'], analyze=True)
    if story:
      return "OK"
    else:
      return 400

  def update(change, project):
    original_values = change['original_values']
    story = Story.query.filter_by(project_id=project.id, external_id=str(change['id'])).first()
    new_values = change['new_values']
    story.text = new_values['name']
    if story.save():
      story.re_chunk()
      story.re_analyze()
      return "OK"
    else:
      return 400

  def delete(change, project):
    story = Story.query.filter_by(project_id=project.id, external_id=str(change['id'])).first()
    story.delete()
    return "OK"

  def get_project(json_data):
    project = json_data['project']
    project = Integration.query.filter_by(integration_project_id=str(project['id'])).first().project
    return project

class Comment(db.Model):
  __versioned__ = {}
  __tablename__ = 'comment'
  id = db.Column(db.Integer, primary_key=True)
  text = db.Column(db.Text, nullable=False)
  error_id = db.Column(db.Integer, db.ForeignKey('error.id'), nullable=False)
  external_id = db.Column(db.String(120), nullable=False)

  def delete(self):
    integration = self.error.project.integration.first()
    story = self.error.story
    threading.Thread(target=self.post_delete_to_pivotal, args=()).start()
    db.session.delete(self)
    db.session.commit()

  def post_delete_to_pivotal(comment_ext_id, story_ext_id, integration_project_id, token):
    c = pycurl.Curl()
    c.setopt(pycurl.URL, "https://www.pivotaltracker.com/services/v5/projects/%s/stories/%s/comments/%s" % (integration_project_id, story_ext_id, comment_ext_id))
    c.setopt(pycurl.HTTPHEADER, ['X-TrackerToken: %s' % token, 'Content-Type: application/json'])
    c.setopt(pycurl.CUSTOMREQUEST,'DELETE')
    c.perform()
    c.close()
    return "OK"
  
  def create(error, story):
    project = story.project
    integration = project.integration.first()
    text = '__' + gettext(error.kind + '_' + error.subkind) + '__' + '\n' + gettext(error.kind + '_' + error.subkind + '_explanation') + '\n' + '__Suggestion__: ' +error.highlight
    if integration:
      response = Comment.post_create_to_pivotal(text, integration, story)
      if response:
        comment = Comment(text=text, external_id=response["id"], error_id=error.id)
        db.session.add(comment)
        db.session.commit()
        db.session.merge(comment)
        return comment
    else:
      return 400

  def post_create_to_pivotal(text, integration, story):
    token = integration.api_token
    data = json.dumps({"text":text})
    buffer = BytesIO()
    c = pycurl.Curl()
    c.setopt(pycurl.URL, "https://www.pivotaltracker.com/services/v5/projects/%s/stories/%s/comments" % (integration.integration_project_id, story.external_id))
    c.setopt(pycurl.HTTPHEADER, ['X-TrackerToken: %s' % token, 'Content-Type: application/json'])
    c.setopt(pycurl.POST,1)
    c.setopt(pycurl.POSTFIELDS, data)
    c.setopt(c.WRITEDATA, buffer)
    c.perform()
    c.close()
    body = buffer.getvalue()
    return json.loads(body.decode())

sa.orm.configure_mappers()