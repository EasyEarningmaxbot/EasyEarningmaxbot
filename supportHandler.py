import logging
from aiogram import Router, types, F, Bot
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

import config
from database import is_banned, get_setting
from startHandler import check_membership

# ১. Aiogram Router ইনিশিয়ালাইজেশন
router = Router()

# -------------------------------------------------------------
# 🎧 'সাপোর্ট' বাটন হ্যান্ডলার (Ultra-Fast & Asynchronous)
# -------------------------------------------------------------
@router.message(F.text.in_(['সাপোর্ট', '🎧 সাপোর্ট']))
async def handle_support(message: types.Message, bot: Bot, state=None):
    try:
        user_id = message.from_user.id
        
        # FSM State ক্লিয়ার করা (যদি কোনো ইন্টারঅ্যাক্টিভ ফর্ম খোলা থাকে)
        if state:
            await state.clear()

        # ব্যান ও মেম্বারশিপ চেক (অ্যাসিঙ্ক)
        if await is_banned(user_id) or not await check_membership(bot, user_id):
            return

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="📢 আমাদের অফিশিয়াল চ্যানেল", url=config.SUPPORT_CHANNEL_LINK)
        )
        
        text = (
            f"🎧 <b>গ্রাহক সেবা কেন্দ্র</b>\n\n"
            f"কোনো সমস্যা বা জিজ্ঞাসার জন্য আমাদের সাপোর্ট চ্যানেলে যুক্ত হোন:\n\n"
            f"🔗 {config.SUPPORT_CHANNEL_LINK}\n\n"
            f"⚠️ <b>নোট:</b> অযথা মেসেজ দেওয়া থেকে বিরত থাকুন। ধন্যবাদ!"
        )

        await message.answer(text, reply_markup=builder.as_markup())

    except Exception as e:
        logging.error(f"Error in handle_support: {e}", exc_info=True)


# -------------------------------------------------------------
# 🆕 'আমি নতুন' বাটন হ্যান্ডলার (URL Validation সহ)
# -------------------------------------------------------------
@router.message(F.text.in_(['আমি নতুন', '🆕 আমি নতুন ❓', '🆕 আমি নতুন']))
async def handle_new_user_guide(message: types.Message, bot: Bot, state=None):
    try:
        user_id = message.from_user.id
        
        if state:
            await state.clear()

        # ব্যান ও মেম্বারশিপ চেক (অ্যাসিঙ্ক)
        if await is_banned(user_id) or not await check_membership(bot, user_id):
            return

        # ডাটাবেস থেকে ভিডিও লিংক রিড করা (অ্যাসিঙ্ক)
        video_url = await get_setting('video_link')
        
        # লিংক যদি ভুল থাকে বা 'http' দিয়ে শুরু না হয়, তবে ডিফল্ট লিংক বসবে
        if not video_url or not str(video_url).startswith(('http://', 'https://')):
            video_url = 'https://youtube.com'

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="🎥 ভিডিওটি দেখুন", url=video_url)
        )

        text = (
            "🆕 <b>কিভাবে কাজ করবেন গাইডলাইন?</b>\n\n"
            "নিচের বাটনে ক্লিক করে কাজের সম্পূর্ণ ভিডিওটি দেখে নিন।"
        )

        await message.answer(text, reply_markup=builder.as_markup())

    except Exception as e:
        logging.error(f"Error in handle_new_user_guide: {e}", exc_info=True)
