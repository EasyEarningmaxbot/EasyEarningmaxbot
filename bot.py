import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

import config
from keyboards import main_menu

# ১. হ্যান্ডলার মডিউলগুলো ইম্পোর্ট
import startHandler
import profileHandler
import referralHandler
import supportHandler
import withdrawHandler
import taskHandler
import adminHandler

# লগিং কনফিগারেশন (সিস্টেমের এরর ট্র্যাক করার জন্য)
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

# ২. বট এবং ডিসপ্যাচার ইনিশিয়ালাইজেশন (সুপারফাস্ট Asynchronous মোড)
bot = Bot(
    token=config.BOT_TOKEN, 
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher(storage=MemoryStorage())

# 🛠️ ৩. রাউটার/হ্যান্ডলার রেজিস্টার করা
# (আপনার হ্যান্ডলার ফাইলগুলোতে router যুক্ত করে এখানে ইনক্লুড করা হচ্ছে)
dp.include_router(startHandler.router)
dp.include_router(profileHandler.router)
dp.include_router(referralHandler.router)
dp.include_router(supportHandler.router)
dp.include_router(withdrawHandler.router)
dp.include_router(taskHandler.router)
dp.include_router(adminHandler.router)


# ❌ ৪. 'বাতিল' বা Cancel হ্যান্ডলার (Asynchronous + Non-blocking)
@dp.message(F.text.contains("বাতিল"))
async def general_cancel(message: types.Message, state=None):
    try:
        # FSM State বা Step ক্লিয়ার করা
        if state:
            await state.clear()
            
        await message.answer(
            "বাতিল করে মূল মেনুতে ফিরে যাওয়া হয়েছে।", 
            reply_markup=await main_menu(message.from_user.id) if callable(main_menu) else main_menu
        )
    except Exception as e:
        logging.error(f"Error in cancel handler: {e}")


# 🛡️ ৫. গ্লোবাল এরর হ্যান্ডলার (যা বটকে কখনো ক্রাশ হতে দেবে না)
@dp.errors()
async def global_error_handler(event: types.ErrorEvent):
    logging.error(f"Critical Exception Caught: {event.exception}", exc_info=True)
    return True


# ⚡ ৬. বটের মূল এক্সিকিউশন
async def main():
    print("⚡ Bot is starting in HIGH-SPEED Async mode...")
    
    # জমে থাকা পুরোনো মেসেজ ক্লিয়ার করা (যাতে বট চালু হওয়ার পর স্লো না হয়ে যায়)
    await bot.delete_webhook(drop_pending_updates=True)
    
    # বোটিং স্টার্ট
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped safely.")
