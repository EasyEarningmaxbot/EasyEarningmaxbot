import logging
from aiogram import Router, types, F, Bot

from database import is_banned, users_col, get_setting
from startHandler import check_membership

# ১. Aiogram Router ইনিশিয়ালাইজেশন
router = Router()

# -------------------------------------------------------------
# 🎁 'আমার রেফারেল' বাটন হ্যান্ডলার (Ultra-Fast & Asynchronous)
# -------------------------------------------------------------
@router.message(F.text.in_(['আমার রেফারেল', '👥 আমার রেফারেল', '🎁 আমার রেফারেল']))
async def handle_referral(message: types.Message, bot: Bot, state=None):
    try:
        user_id = message.from_user.id
        
        # FSM State বা স্টেপ ক্লিয়ার করা (যদি কোনো ফর্ম খোলা থাকে)
        if state:
            await state.clear()

        # ১. ব্যান চেক (অ্যাসিঙ্ক ডাটাবেস রিড)
        if await is_banned(user_id):
            return

        # ২. চ্যানেল মেম্বারশিপ চেক (অ্যাসিঙ্ক এপিআই কল)
        if not await check_membership(bot, user_id):
            return

        # 🔗 ৩. ডায়নামিক বটের ইউজারনেম বের করা
        try:
            bot_info = await bot.get_me()
            bot_username = bot_info.username
        except Exception as e:
            logging.error(f"Error fetching bot username: {e}")
            bot_username = "EasyEarningmaxbot"  # ব্যাকআপ ফলব্যাক ইউজারনেম
            
        ref_link = f"https://t.me/{bot_username}?start={user_id}"

        # ⚡ ৪. সমান্তরালে (Parallel) ডাটাবেস থেকে কাউন্ট, প্রোফাইল ডাটা এবং কমিশন ফেচ করা
        ref_count = await users_col.count_documents({'referrer_id': user_id})
        user_data = await users_col.find_one({'user_id': user_id}, {'ref_income': 1})
        commission = await get_setting('ref_commission') or 10

        ref_income = user_data.get('ref_income', 0.00) if user_data else 0.00

        # 💬 ৫. মেসেজ ফরম্যাট
        ref_text = (
            f'<tg-emoji emoji-id="6312317437840725952">🎁</tg-emoji> <b>আমার রেফারেল</b>\n'
            f'━━━━━━━━━━━━━━━━━━━━━━\n'
            f'<tg-emoji emoji-id="5352861489541714456">🎯</tg-emoji> <b>মোট রেফার:</b> {ref_count} জন\n'
            f'<tg-emoji emoji-id="6190336264940559752">💰</tg-emoji> <b>মোট রেফার ইনকাম:</b> {ref_income:.2f} BDT\n\n'
            f'<tg-emoji emoji-id="4958689671950369798">🔗</tg-emoji> <b>আপনার রেফার লিংক:</b>\n'
            f'<code>{ref_link}</code>\n\n'
            f'<tg-emoji emoji-id="5352980533150259581">📣</tg-emoji> <i>আপনার আমন্ত্রিত ব্যক্তি যা ইনকাম করবে, তার থেকে আপনি {commission}% কমিশন সরাসরি আপনার ব্যালেন্সে পেয়ে যাবেন।</i>'
        )

        # 🚀 ৬. ফাস্ট মেসেজ সেন্ড
        await message.answer(ref_text)

    except Exception as e:
        logging.error(f"Error in handle_referral: {e}", exc_info=True)
