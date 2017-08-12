import json

from flask import Flask, request, jsonify

from models import db, Team, Coupon, Keyword
from error import Error

import config

import telepot
import telepot.helper
from telepot.loop import OrderedWebhook
from telepot.delegate import (
    per_chat_id, create_open, pave_event_space, include_callback_query_chat_id)

with open('produce-permission.json', 'r') as produce_permission_json:
    produce_permission = json.load(produce_permission_json)

with open('teams.json', 'r') as teams_json:
    teams = json.load(teams_json)

try:
    with open('keyword.json', 'r') as keyword_json:
        keywords = json.load(keyword_json)
except:
    keywords = []

app = Flask(__name__)
app.config.from_pyfile('config.py')
db.init_app(app)

for _ in teams:
    try:
        Team(group_id=_['groupId'], name=_['name']).save()
    except:
        pass

if len(keywords) != Keyword.objects.count():
    for _ in keywords:
        Keyword(keyword=_).save()


def generate_coupon(coin, description, producer):
    if coin is None or description is None:
        raise Error("coin and description required")

    coupon = Coupon(coin=coin, description=description, producer=producer)

    try:
        coupon.save()
        return coupon
    except:
        raise Error("invalid value")


def matched_keywrod(keyword_str, group_id):
    keyword = Keyword.objects(keyword=keyword_str).get()

    coin = config.KEYWORD_MATCH_REWARD

    if len(keyword.solved_team) == 0:
        coin *= 2

    coupon = generate_coupon(coin, "解開謎題 獲得", "System")
    team = Team.objects(group_id=group_id).get()

    Keyword.objects(keyword=keyword_str).update_one(push__solved_team=group_id)
    Team.objects(group_id=group_id).update_one(inc__coin=coupon.coin)
    team.reload()
    coupon.own_team = team
    coupon.save()
    bot.sendMessage(team.group_id, "{} {} SITCON Coin\n{} 目前總計擁有 {} SITCON Coin".format(coupon.description, coupon.coin, team.name, team.coin))


@app.route('/generate', methods=['POST'])
def generate():
    token = request.form.get('token')
    coin = request.form.get('coin')
    description = request.form.get('description')

    if token not in produce_permission.keys():
        raise Error("invalid token")

    coupon = generate_coupon(coin, description, produce_permission[token])

    return jsonify({'status': 'OK', 'coupon': str(coupon.id)})


@app.route('/consume', methods=['POST'])
def consume():
    group_id = request.form.get('group_id')
    coupon_id = request.form.get('coupon')

    if group_id is None or coupon_id is None:
        raise Error("group_id and coupon required")

    try:
        coupon = Coupon.objects.with_id(coupon_id)
    except:
        raise Error("invalid coupon id")

    if coupon is None:
        raise Error("invalid coupon id")

    if coupon.own_team is None:
        try:
            team = Team.objects(group_id=group_id).get()
        except:
            raise Error("invalid team id")

        Team.objects(group_id=group_id).update_one(inc__coin=coupon.coin)
        team.reload()
        coupon.own_team = team
        coupon.save()
        bot.sendMessage(team.group_id, "{} {} SITCON Coin\n{} 目前總計擁有 {} SITCON Coin".format(coupon.description, coupon.coin, team.name, team.coin))

        return jsonify({'status': 'OK'})
    else:
        raise Error("Already used", status_code=409)


@app.route('/status')
def status():
    return Team.objects().to_json()


@app.route('/webhook', methods=['GET', 'POST'])
def pass_update():
    webhook.feed(request.data)
    return 'OK'


@app.errorhandler(Error)
def handle_error(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


class TGHandler(telepot.helper.ChatHandler):
    def on_chat_message(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        if content_type is 'text':
            if msg['text'] in keywords:
                matched_keywrod(msg['text'], chat_id)

    def on_callback_query(self, msg):
        self.bot.answerCallbackQuery(msg['id'], url="https://camp.sitcon.party?id=" + str(msg['message']['chat']['id']))


bot = telepot.DelegatorBot(config.BOT_TOKEN, [
    include_callback_query_chat_id(
        pave_event_space())(
            per_chat_id(), create_open, TGHandler, timeout=10),
])

webhook = OrderedWebhook(bot)

try:
    bot.setWebhook(config.WEBHOOK_URI)
except telepot.exception.TooManyRequestsError:
    pass

webhook.run_as_thread()
