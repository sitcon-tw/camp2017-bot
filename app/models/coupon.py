import mongoengine as db
from models import Team


class Coupon(db.Document):
    coin = db.IntField()
    description = db.StringField()
    own_team = db.ReferenceField(Team)
    consume_timestamp = db.IntField()
    producer = db.StringField()
