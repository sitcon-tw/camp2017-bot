from models import db


class Keyword(db.Document):
    keyword = db.StringField(unique=True)
    solved_team = db.ListField(default=[])
