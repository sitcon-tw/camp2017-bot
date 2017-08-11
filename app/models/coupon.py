from models import db
from models import Team


class Coupon(db.Document):
    coin = db.IntField()
    description = db.StringField()
    own_team = db.ReferenceField(Team)
    producer = db.StringField()
