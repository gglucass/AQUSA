Automatic Quality User Story Artisan Prototype - Backend
=======
This is an archived implementation of the AQUSA tool described in http://bit.ly/aqusa-paper

Visit https://github.com/RELabUU/aqusa-core for a more up to date version of the core of the AQUSA algorithm.

### Installation
  * Tested with Python 3.4
  * Install Flask
  * Install libraries using `pip install -r requirements.txt`
  * Create a database
  * run migrations: `./manage.py db migrate` && `./manage.py db upgrade`. You might need to delete the migrations in /migrations/versions first.
  * Install NLTK prerequisite 'Punkt Tokenizer' by running `nltk.download` in the Python interactive shell.
  * Run the translations with `./manage.py translate`. This will throw an error, but this is not a problem.
  * Test if the application works by running `nosetests`
  * Run server by executing ./run.py
  * Run shell by executing ./shell.py

### Instructions for installing the stanford dependency
  * Download the stanford POStagger from
  * Move the files `stanford-postagger-withModel.jar` and `english-left3words-distsim.tagger` to this folder


### Usage
This is the backend of this application, exposing a simple API to be used by front end applications such as a Ruby on Rails web front-end or an iOS mobile client.

* POST to `/unique_string/project/new_story`
* GET stories from `/unique_string/project/stories`
* GET report from `/unique_string/project/report`

As a demo, you can browse to '/unique_string/project/upload_file' and upload a simple CSV. The report page also serves a simple HTML view.

Code Improvements
-------

### Note
This is a prototype application that's still quite difficult to figure out. Future versions will be much improved.
