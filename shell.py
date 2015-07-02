#!/usr/bin/env python

import os
import readline
from pprint import pprint

from flask import *

from app import *
# from utils import *
# from db import *
from app.models import *
from app.analyzers import *


os.environ['PYTHONINSPECT'] = 'True'