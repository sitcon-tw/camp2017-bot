from models import db


class Team(db.Document):
    group_id = db.IntField()
    name = db.StringField()
    coin = db.IntField(default=0)

    meta = {
        'indexes': [
            'group_id'
        ]
    }
