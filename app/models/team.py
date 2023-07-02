import mongoengine as db


class Team(db.Document):
    group_id = db.IntField(unique=True)
    name = db.StringField()
    coin = db.IntField(default=0)

    meta = {
        'indexes': [
            'group_id'
        ]
    }
