import json

import config

from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton

keyboard = InlineKeyboardMarkup(inline_keyboard=[[
    InlineKeyboardButton(text='掃下去', callback_game=True)
]])

bot = Bot(config.BOT_TOKEN)

teams = []
with open('teams.json', 'r') as teams_json:
    teams = json.load(teams_json)

for _ in teams:
    bot.sendGame(_['groupId'], "scanner", reply_markup=keyboard)
