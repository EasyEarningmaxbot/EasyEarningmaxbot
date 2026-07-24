import re
import datetime
import pyotp
import logging
import asyncio
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton, ReplyKeyboardBuilder, KeyboardButton

import config
from database import is_banned, get_setting, tasks_col, is_task_type_active
from keyboards import main_menu, cancel_keyboard
from models import generate_uncommon_username, generate_first_name, generate_last_name
from startHandler import check_membership

router = Router()

# -------------------------------------------------------------
# 🛠️ FSM States (Next Step Handler এর সম্পূর্ণ দ্রুততম বিকল্প)
# -------------------------------------------------------------
class TaskStates(StatesGroup):
    waiting_2fa_key = State()
    waiting_ig_finish = State()
    waiting_fb_uid = State()
    waiting_fb_cookie = State()
    waiting_fb_finish = State()

# -------------------------------------------------------------
# ❌ গ্লোবাল 'বাতিল' বাটন হ্যান্ডলার
# -------------------------------------------------------------
@router.message(F.text == 'বাতিল')
async def handle_global_cancel(message: types.Message, state: FSMContext):
    await state.clear()
    markup = await main_menu(message.from_user.id) if callable(main_menu) else main_menu
    await message.answer("<b>কাজ বাতিল করা হয়েছে।</b>", reply_markup=markup)

# -------------------------------------------------------------
# ⚡ 'কাজ' বাটন ফিল্টারিং হ্যান্ডলার
# -------------------------------------------------------------
@router.message(F.text == 'কাজ')
async def handle_task(message: types.Message, bot: Bot, state: FSMContext):
    user_id = message.from_user.id
    if state: await state.clear()
    
    if await is_banned(user_id) or not await check_membership(bot, user_id):
        return
        
    ig_active = await is_task_type_active('Instagram')
    fb_active = await is_task_type_active('Facebook')

    if not ig_active and not fb_active:
        markup = await main_menu(user_id) if callable(main_menu) else main_menu
        await message.answer("<b>বর্তমানে কোনো কাজ চালু নেই।</b>", reply_markup=markup)
        return

    builder = ReplyKeyboardBuilder()
    if ig_active:
        builder.row(KeyboardButton(text='ইন্সটাগ্রাম কাজ'))
    if fb_active:
        builder.row(KeyboardButton(text='ফেসবুক কাজ'))
        
    builder.row(KeyboardButton(text='বাতিল'))
    
    task_text = (
        '<tg-emoji emoji-id="6082511510406436819">⚡️</tg-emoji>'
        '<b>যেকোনো একটি কাজ সিলেক্ট করুন</b>'
        '<tg-emoji emoji-id="6156513311585211842">⏬</tg-emoji>'
    )
    await message.answer(task_text, reply_markup=builder.as_markup(resize_keyboard=True))

# -------------------------------------------------------------
# 📱 ইন্সটাগ্রাম কাজ হ্যান্ডলার
# -------------------------------------------------------------
@router.message(F.text == 'ইন্সটাগ্রাম কাজ')
async def start_instagram_task_auto(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if await is_banned(user_id): return
    if not await is_task_type_active('Instagram'):
        markup = await main_menu(user_id) if callable(main_menu) else main_menu
        await message.answer("<b>বর্তমানে ইন্সটাগ্রাম কাজ বন্ধ আছে।</b>", reply_markup=markup)
        return

    current_price = await get_setting('price') or 2.70
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=f'ইন্সটাগ্রাম 2fa (৳{current_price:.2f})'))
    builder.row(KeyboardButton(text='বাতিল'))
    
    select_text = '<tg-emoji emoji-id="5213240855892073022">💠</tg-emoji><b>সিলেক্ট করুন:</b>'
    await message.answer(select_text, reply_markup=builder.as_markup(resize_keyboard=True))

@router.message(F.text.startswith('ইন্সটাগ্রাম 2fa'))
async def process_auto_credential_delivery(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if await is_banned(user_id): return
    if not await is_task_type_active('Instagram'):
        markup = await main_menu(user_id) if callable(main_menu) else main_menu
        await message.answer("<b>বর্তমানে ইন্সটাগ্রাম কাজ বন্ধ আছে।</b>", reply_markup=markup)
        return
    
    generated_username = generate_uncommon_username()
    admin_live_password = await get_setting('password') or 'kamrol@22'
    
    # FSM State এ ইউজারের ডেটা সেভ রাখা
    await state.update_data(g_user=generated_username, g_pass=admin_live_password)
    
    task_instruction = (
        f'<tg-emoji emoji-id="6307777408300753473">👤</tg-emoji><b>Username:</b> <code>{generated_username}</code>\n'
        f'<tg-emoji emoji-id="5429405838345265327">🔓</tg-emoji><b>Password:</b> <code>{admin_live_password}</code>\n\n'
        f'<tg-emoji emoji-id="5364310996179503764">📱</tg-emoji><b>উপরের ইউজারনেম এবং পাসওয়ার্ড দিয়ে অ্যাকাউন্ট খুলুন। তারপর নিচে 2FA Set বাটনে ক্লিক করুন</b><tg-emoji emoji-id="5210956306952758910">😄</tg-emoji>'
    )
    
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text='2FA Set'))
    builder.row(KeyboardButton(text='কিভাবে কাজ করব'))
    builder.row(KeyboardButton(text='বাতিল'))
    
    await message.answer(task_instruction, reply_markup=builder.as_markup(resize_keyboard=True))

@router.message(F.text == '2FA Set')
async def trigger_2fa_input_handler(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if await is_banned(user_id): return
    
    data = await state.get_data()
    if not data.get('g_user'):
        g_user = generate_uncommon_username()
        g_pass = await get_setting('password') or "kamrol@22"
        await state.update_data(g_user=g_user, g_pass=g_pass)

    twofa_prompt_text = (
        '<tg-emoji emoji-id="6176966310920983412">🔑</tg-emoji>'
        '<b>2FA Key টি দিন:</b>'
        '<tg-emoji emoji-id="5197474438970363734">⤵️</tg-emoji>'
    )
    
    markup = await cancel_keyboard() if callable(cancel_keyboard) else cancel_keyboard
    await message.answer(twofa_prompt_text, reply_markup=markup)
    await state.set_state(TaskStates.waiting_2fa_key)

@router.message(TaskStates.waiting_2fa_key, F.text != 'বাতিল')
async def validate_and_generate_otp(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    raw_2fa = message.text.strip().replace(" ", "")
    
    markup_cancel = await cancel_keyboard() if callable(cancel_keyboard) else cancel_keyboard
    
    if len(raw_2fa) != 32 or not raw_2fa.isupper() or not re.match(r"^[A-Z2-7]+$", raw_2fa):
        await message.answer("<b>দুঃখিত, এটি কোনো সঠিক 2FA Key নয়!</b>", reply_markup=markup_cancel)
        return

    # ⚡ [Fast Index Check] ১ মিলিসেকেন্ডে ডুপ্লিকেট কি চেক করবে
    existing_task = await tasks_col.find_one({'2fa_key': raw_2fa}, {'_id': 1})
    if existing_task:
        await message.answer("<b>এই 2FA Key টি ইতিমধ্যে ব্যবহার করা হয়েছে! অনুগ্রহ করে নতুন 2FA Key দিন:</b>", reply_markup=markup_cancel)
        return

    try:
        totp = pyotp.TOTP(raw_2fa)
        current_otp = totp.now()
        
        await state.update_data(raw_2fa=raw_2fa)
        
        success_text = (
            "<b>অ্যাকাউন্ট খোলা শেষ হলে নিচের বাটনে চাপ দিন:</b>\n"
            "<b>নিচের কোডটির ওপর চাপ দিলে অটোমেটিক কপি হয়ে যাবে</b> <tg-emoji emoji-id=\"5197474438970363734\">⤵️</tg-emoji>\n\n"
            f"🔑 <code>{current_otp}</code>"
        )
        
        builder = ReplyKeyboardBuilder()
        builder.row(KeyboardButton(text='অ্যাকাউন্ট খোলা শেষ'))
        builder.row(KeyboardButton(text='বাতিল'))
        
        await message.answer(success_text)
        await message.answer("<b>কাজ শেষ হলে নিচের বাটনে ক্লিক করুন:</b>", reply_markup=builder.as_markup(resize_keyboard=True))
        await state.set_state(TaskStates.waiting_ig_finish)
        
    except Exception:
        await message.answer("<b>দুঃখিত, এটি কোনো সঠিক 2FA Key নয়!</b>", reply_markup=markup_cancel)

@router.message(TaskStates.waiting_ig_finish, F.text == 'অ্যাকাউন্ট খোলা শেষ')
async def handle_final_task_submission_step(message: types.Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    data = await state.get_data()
    g_user = data.get('g_user')
    g_pass = data.get('g_pass')
    raw_2fa = data.get('raw_2fa')
    await state.clear()
    
    await tasks_col.insert_one({
        'user_id': user_id,
        'type': 'Instagram',
        'first_name': message.from_user.first_name,
        'username': g_user,
        'password': g_pass,
        '2fa_key': raw_2fa,
        'status': 'Pending Review',
        'submitted_at': datetime.datetime.now()
    })
    
    payment_notice = (
        "<b>এইটার পেমেন্ট ২ ঘন্টা থেকে ৭২ ঘন্টার ভিতর দেওয়া হবে। আরো কাজ করতে থাকেন।</b> "
        '<tg-emoji emoji-id="6235543853747672502">❤️</tg-emoji>'
    )
    markup = await main_menu(user_id) if callable(main_menu) else main_menu
    await message.answer(payment_notice, reply_markup=markup)
    
    group_task_text = (
        "<b>নতুন কাজ জমা হয়েছে!</b>\n\n"
        f"<b>Type:</b> Instagram\n"
        f"<b>User ID:</b> <code>{user_id}</code>\n"
        f"<b>Name:</b> {message.from_user.first_name}\n"
        f"<b>Username:</b> <code>{g_user}</code>"
    )
    try:
        await bot.send_message(config.TASK_LOG_GROUP_ID, group_task_text)
    except Exception as e:
        logging.error(f"Task Group Log Error: {e}")

# -------------------------------------------------------------
# 📘 ফেসবুক কাজ হ্যান্ডলার
# -------------------------------------------------------------
@router.message(F.text == 'ফেসবুক কাজ')
async def handle_facebook_task(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if await is_banned(user_id): return
    if not await is_task_type_active('Facebook'):
        markup = await main_menu(user_id) if callable(main_menu) else main_menu
        await message.answer("<b>বর্তমানে ফেসবুক কাজ বন্ধ আছে।</b>", reply_markup=markup)
        return

    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text='Anymail/Number'))
    builder.row(KeyboardButton(text='বাতিল'))
    
    select_text = '<tg-emoji emoji-id="5213240855892073022">💠</tg-emoji> <b>সিলেক্ট করুন:</b>'
    await message.answer(select_text, reply_markup=builder.as_markup(resize_keyboard=True))

@router.message(F.text == 'Anymail/Number')
async def handle_anymail_number(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if await is_banned(user_id): return
    if not await is_task_type_active('Facebook'):
        markup = await main_menu(user_id) if callable(main_menu) else main_menu
        await message.answer("<b>বর্তমানে ফেসবুক কাজ বন্ধ আছে।</b>", reply_markup=markup)
        return

    fb_price = await get_setting('fb_price') or 0.00
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=f'0 fnd cookies | {fb_price:.2f}৳'))
    builder.row(KeyboardButton(text='বাতিল'))
    
    select_text = '<tg-emoji emoji-id="5213240855892073022">💠</tg-emoji> <b>সিলেক্ট করুন:</b>'
    await message.answer(select_text, reply_markup=builder.as_markup(resize_keyboard=True))

@router.message(F.text.startswith('0 fnd cookies'))
async def process_facebook_credentials(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if await is_banned(user_id): return
    if not await is_task_type_active('Facebook'):
        markup = await main_menu(user_id) if callable(main_menu) else main_menu
        await message.answer("<b>বর্তমানে ফেসবুক কাজ বন্ধ আছে।</b>", reply_markup=markup)
        return
    
    fname = generate_first_name() if callable(generate_first_name) else "First"
    lname = generate_last_name() if callable(generate_last_name) else "Last"
    admin_fb_pass = await get_setting('fb_password') or await get_setting('password') or 'kamrol@22'
    
    info_text = (
        f'<tg-emoji emoji-id="5352861489541714456">👤</tg-emoji> <b>First name:</b> <code>{fname}</code>\n'
        f'<tg-emoji emoji-id="5352861489541714456">👤</tg-emoji> <b>Last name:</b> <code>{lname}</code>\n'
        f'<tg-emoji emoji-id="5429405838345265327">🔑</tg-emoji> <b>Password:</b> <code>{admin_fb_pass}</code>\n\n'
        f'<tg-emoji emoji-id="5188344996356448758">📱</tg-emoji> <b>উপরের তথ্য দিয়ে অ্যাকাউন্ট খুলে নিচে Send UID বাটনে চাপ দিন</b> <tg-emoji emoji-id="5456258317477230911">👇</tg-emoji>'
    )
    
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text='Send UID'))
    builder.row(KeyboardButton(text='কিভাবে কাজ করব'))
    builder.row(KeyboardButton(text='বাতিল'))
    
    await message.answer(info_text, reply_markup=builder.as_markup(resize_keyboard=True))

@router.message(F.text == 'Send UID')
async def prompt_facebook_uid(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if await is_banned(user_id): return
    
    prompt_text = (
        '<b>আপনার</b> <tg-emoji emoji-id="5389064576333527180">🆔</tg-emoji> '
        '<b>Facebook UID দিন:</b>'
    )
    
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text='বাতিল'))
    
    await message.answer(prompt_text, reply_markup=builder.as_markup(resize_keyboard=True))
    await state.set_state(TaskStates.waiting_fb_uid)

@router.message(TaskStates.waiting_fb_uid, F.text != 'বাতিল')
async def validate_facebook_uid(message: types.Message, state: FSMContext):
    uid = message.text.strip()
    
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text='বাতিল'))
    cancel_markup = builder.as_markup(resize_keyboard=True)
    
    if len(uid) < 14 or not uid.isdigit():
        prompt_err = '<tg-emoji emoji-id="4958526153955476488">⚠️</tg-emoji> <b>দয়া করে আপনি আপনার সঠিক UID সেন্ড করুন:</b>'
        await message.answer(prompt_err, reply_markup=cancel_markup)
        return

    # ⚡ [Fast Index Check] fast UID lookup
    existing_uid = await tasks_col.find_one({'fb_uid': uid}, {'_id': 1})
    if existing_uid:
        dup_err = '<b>দুঃখিত আপনি এই UID একবার সেন্ট করেছেন দ্বিতীয়বার নেওয়া যাবে না</b> <tg-emoji emoji-id="4958526153955476488">❌</tg-emoji>'
        await message.answer(dup_err, reply_markup=cancel_markup)
        return

    await state.update_data(fb_uid=uid)
    cookie_prompt = '<b>আপনার Cookie দিন</b> <tg-emoji emoji-id="5197474438970363734">⤵️</tg-emoji>'
    await message.answer(cookie_prompt, reply_markup=cancel_markup)
    await state.set_state(TaskStates.waiting_fb_cookie)

@router.message(TaskStates.waiting_fb_cookie, F.text != 'বাতিল')
async def collect_facebook_cookie(message: types.Message, state: FSMContext):
    cookie_text = message.text.strip()
    await state.update_data(fb_cookie=cookie_text)
    
    finish_prompt = '<tg-emoji emoji-id="6298612102709909362">⚙️</tg-emoji> <b>সম্পূর্ণ করতে নিচের বাটনে চাপুন:</b>'
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text='অ্যাকাউন্ট খোলা শেষ'))
    builder.row(KeyboardButton(text='বাতিল'))
    
    await message.answer(finish_prompt, reply_markup=builder.as_markup(resize_keyboard=True))
    await state.set_state(TaskStates.waiting_fb_finish)

@router.message(TaskStates.waiting_fb_finish, F.text == 'অ্যাকাউন্ট খোলা শেষ')
async def finalize_facebook_submission(message: types.Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    data = await state.get_data()
    fb_uid = data.get('fb_uid')
    fb_cookie = data.get('fb_cookie')
    await state.clear()
    
    await tasks_col.insert_one({
        'user_id': user_id,
        'type': 'Facebook',
        'fb_uid': fb_uid,
        'fb_cookie': fb_cookie,
        'status': 'Pending Review',
        'submitted_at': datetime.datetime.now()
    })
    
    success_notice = (
        '<tg-emoji emoji-id="6125457176161948466">✅</tg-emoji> '
        '<tg-emoji emoji-id="5389064576333527180">📘</tg-emoji> '
        '<b>Facebook কাজ সফলভাবে জমা হয়েছে!</b>'
    )
    markup = await main_menu(user_id) if callable(main_menu) else main_menu
    await message.answer(success_notice, reply_markup=markup)
    
    group_task_text = (
        "<b>নতুন ফেসবুক কাজ জমা হয়েছে!</b>\n\n"
        f"<b>Type:</b> Facebook\n"
        f"<b>User ID:</b> <code>{user_id}</code>\n"
        f"<b>FB UID:</b> <code>{fb_uid}</code>"
    )
    try:
        await bot.send_message(config.TASK_LOG_GROUP_ID, group_task_text)
    except Exception as e:
        logging.error(f"Task Group Log Error: {e}")

# -------------------------------------------------------------
# 🎥 কিভাবে কাজ করব (ভিডিও গাইড)
# -------------------------------------------------------------
@router.message(F.text == 'কিভাবে কাজ করব')
async def send_video_guide(message: types.Message):
    user_id = message.from_user.id
    if await is_banned(user_id): return
    video_url = await get_setting('video_link')
    if not video_url or not str(video_url).startswith(('http://', 'https://')):
        video_url = 'https://youtube.com'
        
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="ভিডিওটি দেখুন", url=video_url))
    await message.answer("<b>কাজের নিয়ম দেখার জন্য নিচের ভিডিও বাটনে ক্লিক করুন:</b>", reply_markup=builder.as_markup())
