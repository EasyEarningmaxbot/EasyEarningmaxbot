import telebot
from telebot import apihelper

import config
from keyboards import main_menu

# Bot instance setup
apihelper.CONNECT_TIMEOUT = 60
apihelper.READ_TIMEOUT = 60
bot = telebot.TeleBot(config.BOT_TOKEN, num_threads=100)

# Import Handlers
import startHandler
import profileHandler
import referralHandler
import supportHandler
import withdrawHandler
import taskHandler
import adminHandler

# 🛠️ Register Handlers (Profile Handler কে উপরে দেওয়া হয়েছে)
profileHandler.register(bot)
startHandler.register(bot)
referralHandler.register(bot)
supportHandler.register(bot)
withdrawHandler.register(bot)
taskHandler.register(bot)
adminHandler.register(bot)

@bot.message_handler(func=lambda message: message.text and 'বাতিল' in message.text)
def general_cancel(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    bot.send_message(message.chat.id, "বাতিল করে মূল মেনুতে ফিরে যাওয়া হয়েছে।", reply_markup=main_menu(message.from_user.id))

@bot.message_handler(func=lambda message: True)
def fallback_handler(message):
    pass

if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling(timeout=60)
