from datetime import datetime
import logging
import json
import time

from flask import Flask, request, jsonify, abort
from mongoengine import NotUniqueError, ValidationError

from telebot import TeleBot
from telebot.util import quick_markup
from telebot.types import Update

from models import Team, Coupon, Keyword
from error import Error

import config

with open('produce-permission.json', 'r') as produce_permission_json:
    produce_permission = json.load(produce_permission_json)

with open('teams.json', 'r') as teams_json:
    teams = json.load(teams_json)

try:
    with open('keyword.json', 'r') as keyword_json:
        keywords = json.load(keyword_json)
        for key in keywords.keys():
            if "description" not in keywords[key]:
                keywords[key]["description"] = config.DEFAULT_KEYWORD_DESCRIPTION
except IOError:
    keywords = {}


bot = TeleBot(config.BOT_TOKEN)
app = Flask(__name__)
app.config.from_pyfile('config.py')
app.logger.addHandler(logging.StreamHandler())
app.logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

for _ in teams:
    try:
        Team(group_id=_['groupId'], name=_['name']).save()
    except NotUniqueError:
        pass

if len(keywords.keys()) != Keyword.objects.count():
    for k, v in keywords.items():
        Keyword(keyword=k, **dict(filter(lambda pair: pair[0] != "value", v.items()))).save()


def generate_coupon(coin, description, producer):
    if coin is None or description is None:
        raise Error("coin and description required")

    coupon = Coupon(coin=coin, description=description, producer=producer)

    try:
        coupon.save()
        return coupon
    except ValidationError:
        raise Error("invalid value")


def consume_coupon(coupon: Coupon, team: Team, log_message: str):
    if coupon.own_team is not None:
        raise Error("coupon used")

    Team.objects(group_id=team.group_id).update_one(inc__coin=coupon.coin)
    team.reload()
    coupon.own_team = team
    coupon.save()
    team.reload()
    bot.send_message(team.group_id, "{} {} {currency_name}\n{} 目前總計擁有 {} {currency_name}"
                    .format(coupon.description, coupon.coin, team.name, team.coin, currency_name=config.CURRENCY_NAME))

    app.logger.info("{}, {} {} and gained {} coin".format(str(datetime.now()), team.name, log_message, coupon.coin))


@bot.callback_query_handler(func=lambda x: True)
def send_scanner(callback_query):
    try:
        bot.answer_callback_query(callback_query.id, url="https://camp.sitcon.party?id=" + str(callback_query.message.chat.id))
    except AttributeError:
        # not click from group, chat id not found
        pass


@bot.message_handler(content_types=['text'], chat_types=['group', 'supergroup'])
def message_receive(message):
    if message.text in keywords.keys():
        matched_keyword(message.text, message.chat.id)

    if message.text == config.SCANNER_KEYWORD:
        keyboard = quick_markup({
            config.SCANNER_BUTTON_TEXT: {'callback_game': True}
        })
        bot.send_game(message.chat.id, "scanner", reply_markup=keyboard)


def matched_keyword(keyword_str, group_id):
    keyword = Keyword.objects(keyword=keyword_str).get()

    if group_id in keyword.solved_team:
        return

    team = Team.objects(group_id=group_id).get()

#     if keyword_str == "238504":
#         bot.sendMessage(team.group_id, "「副市長是受小石信任之人，是心靈純潔之人」")
#     elif keyword_str == "15769":
#         bot.sendMessage(team.group_id, "「市長是小石害怕之人，是已經受到心靈扭曲影響之人」")

    coin = config.KEYWORD_MATCH_REWARD * keywords[keyword_str]["value"]

    keyword.reload()
    if keyword.first_bonus:
        coin *= 2
        keyword.first_bonus = False
        keyword.save()

    coupon = generate_coupon(coin, keyword.description, "System")

    Keyword.objects(keyword=keyword_str).update_one(push__solved_team=group_id)
    consume_coupon(coupon, team, f"solved keyword {keyword_str}")


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
        except Team.DoesNotExist:
            raise Error("invalid team id")

        consume_coupon(coupon, team, "consumed coupon")

#         if len(set(map(lambda _: _.producer, Coupon.objects(own_team=team)))) == len(produce_permission.keys()):
#             bot.sendMessage(team.group_id, "「書靈 Lamp 想要幫助學徒尋找真相，因此靠著自己淵博的知識，發動了一個『真實之陣』\n真實之陣，信任正確之人，訴說你的信號，將會返回試金之結論」")

        return jsonify({'status': 'OK'})
    else:
        raise Error("Already used", status_code=409)


@app.route('/status')
def status():
    token = request.args.get('staff_token')
    return_object = Team.objects()
    if token != config.STAFF_TOKEN:
        return_object = return_object.none()
    return return_object.to_json()


@app.route('/keyword_status')
def keyword_status():
    access_list = ['solved_team']
    token = request.args.get('staff_token')
    if token == config.STAFF_TOKEN:
        access_list.append('keyword')
    return Keyword.objects().only(*access_list).to_json()


# Process webhook calls
@app.route('/webhook', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        abort(403)


@app.route('/teams')
def get_teams():
    return jsonify(teams)


@app.errorhandler(Error)
def handle_error(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


bot.remove_webhook()
time.sleep(0.1)
# polling is for develop
# bot.infinity_polling()
bot.set_webhook(url=config.WEBHOOK_URI)
