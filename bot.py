import telebot
from telebot import apihelper

import config
from keyboards import main_menu

# API টাইমআউট কিছুটা কমিয়ে দ্রুত রেসপন্সের জন্য অপটিমাইজ করা হলো
apihelper.CONNECT_TIMEOUT = 10
apihelper.READ_TIMEOUT = 10

# Thread সংখ্যা কমসে কম ১০-২০ এর মধ্যে রাখা নিরাপদ
bot = telebot.TeleBot(config.BOT_TOKEN, num_threads=20, parse_mode="HTML")

# Import Handlers
import startHandler
import profileHandler
import referralHandler
import supportHandler
import withdrawHandler
import taskHandler
import adminHandler

# 🛠️ Register Handlers
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

if __name__ == "__main__":
    print("Bot is running fast...")
    # non_stop=True এবং skip_pending=True দিলে জমে থাকা পুরোনো রিকোয়েস্টের কারণে বট স্লো হবে না
    bot.infinity_polling(timeout=10, long_polling_timeout=5, skip_pending=True)
