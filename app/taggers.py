import nltk
from nltk.tag.stanford import POSTagger
import time
import pexpect

class StanfordTagger(object):

  def __init__(self):
    cmd = 'java -mx300m -cp stanford/stanford-postagger-withModel.jar edu.stanford.nlp.tagger.maxent.MaxentTagger -model stanford/english-left3words-distsim.tagger'
    self.pos_tagger = pexpect.spawn(cmd)
    self.pos_tagger.expect('done', timeout=20)
    print('Initialized StanfordTagger')

  def _parse(self, text):
    # clean up any leftover results
    while True:
      try:
          self.pos_tagger.read_nonblocking(4000, 0.25)
      except pexpect.TIMEOUT:
          break

    # send the actual text
    self.pos_tagger.sendline(text)

    max_expected_time = min(40, 3 + len(text) / 20.0)
    end_time = time.time() + max_expected_time

    incoming = ""
    while True:
      # Time left, read more data
      try:
        incoming += self.pos_tagger.read_nonblocking(2000, 0.5).decode('utf-8')
        if "_" in incoming: 
            break
        time.sleep(0.0001)
      except pexpect.TIMEOUT:
        if end_time - time.time() < 0:
          # logger.error("Error: Timeout with input '%s'" % (incoming))
          return {'error': "timed out after %f seconds" % max_expected_time}
        else:
          continue
      except pexpect.EOF:
        break

    tagged_list = list(filter(None, incoming.split('\r\n')))
    tagged_string = [item for item in tagged_list if item not in [text]][0]
    result = POSTagger.parse_output(POSTagger, tagged_string)
    return result

  def parse(self, text):
    response = self._parse(text)
    return response

class NLTKTagger(object):
  def parse(self, text):
    sentences = nltk.sent_tokenize(text)
    sentences = [nltk.word_tokenize(sent) for sent in sentences]
    sentences = [nltk.pos_tag(sent) for sent in sentences]
    return sentences
