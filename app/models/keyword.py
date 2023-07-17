import mongoengine as db
import config


class Keyword(db.Document):
    keyword = db.StringField(unique=True)
    solved_team = db.ListField(default=[])
    first_bonus = db.BooleanField(default=True)
    description = db.StringField()
