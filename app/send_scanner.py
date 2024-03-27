import json

import config

from telebot import TeleBot
from telebot.util import quick_markup

keyboard = quick_markup({
    config.SCANNER_BUTTON_TEXT: {'callback_game': True}
})

bot = TeleBot(config.BOT_TOKEN)

teams = []
with open('teams.json', 'r') as teams_json:
    teams = json.load(teams_json)

for _ in teams:
    bot.send_game(_['groupId'], "scanner", reply_markup=keyboard)
