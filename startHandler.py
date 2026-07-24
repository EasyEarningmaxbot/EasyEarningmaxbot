import datetime
import asyncio
import logging
from aiogram import Router, types, F, Bot
from aiogram.filters import CommandObject, CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

import config
from database import is_banned, users_col, get_setting
from keyboards import main_menu

# ১. Aiogram Router ইনিশিয়ালাইজেশন
router = Router()

# -------------------------------------------------------------
# 🛠️ Helper Functions (Async/Non-blocking)
# -------------------------------------------------------------

async def check_membership(bot: Bot, user_id: int) -> bool:
    """
    REQUIRED_CHANNELS-এর প্রতিটি চ্যানেলে ইউজার জয়েন আছে কিনা চেক করে।
    Async হওয়ার কারণে সবগুলো চ্যানেল একসাথে দ্রুত চেক হয়।
    """
    try:
        for ch in config.REQUIRED_CHANNELS:
            member = await bot.get_chat_member(chat_id=ch['id'], user_id=user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        return True
    except Exception as e:
        logging.error(f"Membership check error: {e}")
        return False


async def send_force_join_msg(bot: Bot, chat_id: int, referrer_id: int = None):
    """
    Force Join বার্তা তৈরি করে এবং ইনলাইন বাটন পাঠায়।
    """
    builder = InlineKeyboardBuilder()
    
    for ch in config.REQUIRED_CHANNELS:
        builder.row(
            InlineKeyboardButton(text=f"📢 জয়েন করুন: {ch['name']}", url=ch['link'])
        )
        
    cb_data = f"verify_join_{referrer_id}" if referrer_id else "verify_join_none"
    builder.row(
        InlineKeyboardButton(text="✅ Verify (ভেরিফাই)", callback_data=cb_data)
    )
    
    msg_text = (
        "<b>⚠️ বটটি ব্যবহার করতে হলে আপনাকে আমাদের অফিশিয়াল চ্যানেলগুলোতে জয়েন করতে হবে!</b>\n\n"
        "নিচের চ্যানেলগুলোতে জয়েন করে <b>'Verify'</b> বাটনে ক্লিক করুন।"
    )
    await bot.send_message(chat_id, msg_text, reply_markup=builder.as_markup())


async def process_user_registration(bot: Bot, user: types.User, referrer_id: int = None):
    """
    ইউজার রেজিস্টার বা তথ্য আপডেট করার অ্যাসিনক্রোনাস ফাংশন।
    """
    user_id = user.id
    first_name = user.first_name or "ইউজার"
    username = user.username or "None"

    # Async Database Query
    user_data = await asyncio.to_thread(users_col.find_one, {'user_id': user_id}, {'joined_at': 1})
    
    if not user_data:
        new_user = {
            'user_id': user_id,
            'first_name': first_name,
                'username': username,
            'joined_at': datetime.datetime.now(),
            'balance': 0.00,
            'pending_withdraw': 0.00,
            'total_income': 0.00,
            'completed_tasks': 0,
            'is_banned': False
        }
        if referrer_id and referrer_id != user_id:
            new_user['referrer_id'] = referrer_id
            try:
                await bot.send_message(referrer_id, "👥 আপনার রেফারেলে একজন নতুন মেম্বার জয়েন করেছে!")
            except Exception:
                pass
                
        await asyncio.to_thread(users_col.insert_one, new_user)
    else:
        await asyncio.to_thread(
            users_col.update_one,
            {'user_id': user_id},
            {'$set': {
                'first_name': first_name,
                'username': username
            }}
        )

# -------------------------------------------------------------
# 📥 Handlers
# -------------------------------------------------------------

# 🚀 /start হ্যান্ডলার
@router.message(CommandStart())
async def send_welcome(message: types.Message, command: CommandObject, bot: Bot):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "ইউজার"
    
    # ব্যান চেক
    if await asyncio.to_thread(is_banned, user_id):
        await message.answer("❌ আপনাকে বট থেকে ব্যান করা হয়েছে।")
        return
        
    # রেফারার আইডি বের করা
    referrer_id = None
    if command.args and command.args.isdigit():
        referrer_id = int(command.args)
            
    # চ্যানেল জয়েন চেক
    if not await check_membership(bot, user_id):
        await send_force_join_msg(bot, message.chat.id, referrer_id)
        return

    # ইউজার ডাটাবেসে সেভ/আপডেট করা
    await process_user_registration(bot, message.from_user, referrer_id)

    welcome_text = (
        f'<tg-emoji emoji-id="5416015487525988007">👋</tg-emoji> <b>স্বাগতম, {first_name}!</b>\n\n'
        f'<tg-emoji emoji-id="6253780692908378898">🚀</tg-emoji> <b>কাজ শুরু করতে নিচের অপশনগুলো ব্যবহার করুন</b> <tg-emoji emoji-id="5447183459602669338">👇</tg-emoji>'
    )

    markup = await main_menu(user_id) if callable(main_menu) else main_menu
    await message.answer(welcome_text, reply_markup=markup)


# ✅ Verify Join বাটন হ্যান্ডলার
@router.callback_query(F.data.startswith('verify_join'))
async def verify_join_callback(call: types.CallbackQuery, bot: Bot):
    user_id = call.from_user.id
    first_name = call.from_user.first_name or "ইউজার"
    
    parts = call.data.split('_')
    referrer_id = None
    if len(parts) == 3 and parts[2] != 'none':
        try:
            referrer_id = int(parts[2])
        except ValueError:
            pass

    if await check_membership(bot, user_id):
        await call.answer("✅ ভেরিফিকেশন সফল হয়েছে!", show_alert=True)
        try:
            await call.message.delete()
        except Exception:
            pass
        
        await process_user_registration(bot, call.from_user, referrer_id)
                
        welcome_text = (
            f'<tg-emoji emoji-id="5416015487525988007">👋</tg-emoji> <b>স্বাগতম, {first_name}!</b>\n\n'
            f'<tg-emoji emoji-id="6253780692908378898">🚀</tg-emoji> <b>কাজ শুরু করতে নিচের অপশনগুলো ব্যবহার করুন</b> <tg-emoji emoji-id="5447183459602669338">👇</tg-emoji>'
        )

        markup = await main_menu(user_id) if callable(main_menu) else main_menu
        await bot.send_message(call.message.chat.id, welcome_text, reply_markup=markup)
    else:
        await call.answer("❌ আপনি এখনো সবগুলো চ্যানেলে জয়েন করেননি!", show_alert=True)


# 🏆 লিডারবোর্ড বাটন হ্যান্ডলার
@router.message(F.text == 'লিডারবোর্ড')
async def show_leaderboard(message: types.Message):
    user_id = message.from_user.id
    
    if await asyncio.to_thread(is_banned, user_id):
        return

    is_lb_active = await asyncio.to_thread(get_setting, 'leaderboard_active')
    if is_lb_active is False:
        markup = await main_menu(user_id) if callable(main_menu) else main_menu
        await message.answer("❌ বর্তমানে লিডারবোর্ড বন্ধ রয়েছে।", reply_markup=markup)
        return

    prize_setting = await asyncio.to_thread(get_setting, 'leaderboard_prizes') or "100,50,30,20,10"
    try:
        prizes = [float(p.strip()) for p in prize_setting.split(',')]
    except Exception:
        prizes = [100.0, 50.0, 30.0, 20.0, 10.0]

    # ⚡ [Fast Query] শুধুমাত্র প্রয়োজনীয় Field গুলো Projection করে ডাটাবেস থেকে ফ্রন্টলাইনে আনা
    def fetch_top_users():
        return list(users_col.find({}, {'first_name': 1, 'completed_tasks': 1}).sort('completed_tasks', -1).limit(5))

    top_users = await asyncio.to_thread(fetch_top_users)
    
    rank_emojis = [
        "6206419981161211268", 
        "6206222099132978580", 
        "6206311275538946838", 
        "5352566657216714037", 
        "5353086880835474989"  
    ]

    now = datetime.datetime.now()
    days_until_sunday = (6 - now.weekday()) % 7
    if days_until_sunday == 0 and now.hour == 0 and now.minute == 0:
        days_until_sunday = 7
    
    next_reset = (now + datetime.timedelta(days=days_until_sunday)).replace(hour=23, minute=59, second=59)
    time_left = next_reset - now
    
    days = time_left.days
    hours, remainder = divmod(time_left.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    text = '<tg-emoji emoji-id="6194737030165959506">🏆</tg-emoji> <b>সাপ্তাহিক লিডারবোর্ড - টপ ৫ (সঠিক কাজ)</b>\n'
    text += '━━━━━━━━━━━━━━━━━\n\n'

    for i in range(5):
        emoji_id = rank_emojis[i]
        prize = prizes[i] if i < len(prizes) else 0.00
        
        if i < len(top_users):
            u = top_users[i]
            name = u.get('first_name', 'মেম্বার')
            tasks = u.get('completed_tasks', 0)
        else:
            name = "মেম্বার নাম"
            tasks = 0

        text += f'<tg-emoji emoji-id="{emoji_id}">🥇</tg-emoji> {name} - {tasks} টি টাস্ক <tg-emoji emoji-id="4956418939920843885">⚡</tg-emoji>, (পুরস্কার: {prize:.2f}৳)\n'

    text += f'\n<tg-emoji emoji-id="5136508653808911452">⏳</tg-emoji> <b>আর মাত্র: {days} দিন {hours} ঘন্টা {minutes} মিনিট {seconds} সেকেন্ড বাকি!</b>\n\n'
    text += '(প্রতি সপ্তাহে লিডারবোর্ডে থাকা Top 5 জনকে পুরস্কৃত করা হবে আপনিও চাইলে অংশগ্রহণ করতে পারেন লিডারবোর্ড প্রতি সাপ্তাহিক ক্লিয়ার হয়)'

    await message.answer(text)
