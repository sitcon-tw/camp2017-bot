from datetime import datetime
import logging
import json

from flask import Flask, request, jsonify
from mongoengine import NotUniqueError, ValidationError
from flask_mongoengine import DoesNotExist

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
except IOError:
    keywords = {}

app = Flask(__name__)
app.config.from_pyfile('config.py')
db.init_app(app)
app.logger.addHandler(logging.StreamHandler())
app.logger.setLevel(logging.INFO)

for _ in teams:
    try:
        Team(group_id=_['groupId'], name=_['name']).save()
    except NotUniqueError:
        pass

if len(keywords.keys()) != Keyword.objects.count():
    for _ in keywords.keys():
        Keyword(keyword=_).save()


def generate_coupon(coin, description, producer):
    if coin is None or description is None:
        raise Error("coin and description required")

    coupon = Coupon(coin=coin, description=description, producer=producer)

    try:
        coupon.save()
        return coupon
    except ValidationError:
        raise Error("invalid value")


def matched_keywrod(keyword_str, group_id):
    keyword = Keyword.objects(keyword=keyword_str).get()

    if group_id in keyword.solved_team:
        return

    team = Team.objects(group_id=group_id).get()

#     if keyword_str == "238504":
#         bot.sendMessage(team.group_id, "「副市長是受小石信任之人，是心靈純潔之人」")
#     elif keyword_str == "15769":
#         bot.sendMessage(team.group_id, "「市長是小石害怕之人，是已經受到心靈扭曲影響之人」")

    coin = config.KEYWORD_MATCH_REWARD * keywords[keyword_str]

    if len(keyword.solved_team) == 0:
        coin *= 2

    coupon = generate_coupon(coin, "解開謎題 獲得", "System")

    Keyword.objects(keyword=keyword_str).update_one(push__solved_team=group_id)
    Team.objects(group_id=group_id).update_one(inc__coin=coupon.coin)
    team.reload()
    coupon.own_team = team
    coupon.save()
    bot.sendMessage(team.group_id, "{} {} 小石幣\n{} 目前總計擁有 {} 小石幣".format(coupon.description, coupon.coin, team.name, team.coin))
    app.logger.info("{}, {} solved keyword {} gain {} coin".format(str(datetime.now()), team.name, keyword_str, coupon.coin))


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
    except ValidationError:
        raise Error("invalid coupon id")

    if coupon is None:
        raise Error("invalid coupon id")

    if coupon.own_team is None:
        try:
            team = Team.objects(group_id=group_id).get()
        except DoesNotExist:
            raise Error("invalid team id")

        Team.objects(group_id=group_id).update_one(inc__coin=coupon.coin)
        team.reload()
        coupon.own_team = team
        coupon.save()
        bot.sendMessage(team.group_id, "{} {} 小石幣\n{} 目前總計擁有 {} 小石幣".format(coupon.description, coupon.coin, team.name, team.coin))

#         if len(set(map(lambda _: _.producer, Coupon.objects(own_team=team)))) == len(produce_permission.keys()):
#             bot.sendMessage(team.group_id, "「書靈 Lamp 想要幫助學徒尋找真相，因此靠著自己淵博的知識，發動了一個『真實之陣』\n真實之陣，信任正確之人，訴說你的信號，將會返回試金之結論」")

        return jsonify({'status': 'OK'})
    else:
        raise Error("Already used", status_code=409)


@app.route('/status')
def status():
    return Team.objects().to_json()


@app.route('/keyword_status')
def keyword_status():
    return Keyword.objects().only('solved_team').to_json()


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
            if msg['text'] in keywords.keys():
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
