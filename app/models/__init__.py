from mongoengine import connect

import config

connect(**config.MONGODB_SETTINGS)

from models.team import *
from models.coupon import *
from models.keyword import *
