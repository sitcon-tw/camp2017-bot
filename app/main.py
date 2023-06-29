from datetime import datetime
import logging
import json

from flask import Flask, request, jsonify
from mongoengine import NotUniqueError, ValidationError
from flask_mongoengine import DoesNotExist

from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import filters, ApplicationBuilder, CallbackQueryHandler, MessageHandler

from models import db, Team, Coupon, Keyword
from error import Error

import config

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
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

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


async def scanner_callback(update, context):
    try:
        await context.bot.answerCallbackQuery(update.callback_query.id, url="https://camp.sitcon.party?id=" + str(update.callback_query.message.chat.id))
    except AttributeError:
        # not click from group, chat id not found
        pass


async def match_keyword_callback(update, context):
    if update.message.text in keywords.keys():
        await matched_keyword(update.message.text, update.message.chat.id, context.bot)

    if update.message.text == "掃描點數":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=config.SCANNER_BUTTON_TEXT, callback_game=True)
        ]])
        await context.bot.sendGame(update.message.chat.id, "scanner", reply_markup=keyboard)


async def matched_keyword(keyword_str, group_id, bot):
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

    await bot.sendMessage(team.group_id, "{} {} {currency_name}\n{} 目前總計擁有 {} {currency_name}"
                    .format(coupon.description, coupon.coin, team.name, team.coin, currency_name=config.CURRENCY_NAME))
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
async def consume():
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
        await bot.sendMessage(team.group_id, "{} {} {currency_name}\n{} 目前總計擁有 {} {currency_name}"
                        .format(coupon.description, coupon.coin, team.name, team.coin, currency_name=config.CURRENCY_NAME))

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
    update_queue.put(Update.de_json(request.get_json(force=True), bot))
    return 'OK'


@app.errorhandler(Error)
def handle_error(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


def tg_bot_init(config):
    application = ApplicationBuilder().token(config.BOT_TOKEN).build()
    bot = application.bot
    update_queue = application.update_queue

    application.add_handler(MessageHandler(filters.TEXT, match_keyword_callback))
    application.add_handler(CallbackQueryHandler(scanner_callback))

    application.run_polling()

    return (bot, update_queue)


bot, update_queue = tg_bot_init(config)
