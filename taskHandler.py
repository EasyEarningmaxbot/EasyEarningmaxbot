import re
import datetime
import pyotp
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import config
from database import is_banned, get_setting, tasks_col, is_task_type_active
from keyboards import main_menu, cancel_keyboard
from models import generate_uncommon_username, generate_first_name, generate_last_name
from startHandler import check_membership

def register(bot):
    # ❌ গ্লোবাল 'বাতিল' বাটন হ্যান্ডলার
    @bot.message_handler(func=lambda message: message.text == 'বাতিল')
    def handle_global_cancel(message):
        bot.clear_step_handler_by_chat_id(message.chat.id)
        bot.send_message(message.chat.id, "<b>কাজ বাতিল করা হয়েছে।</b>", parse_mode="HTML", reply_markup=main_menu(message.from_user.id))

    # ------------------ 'কাজ' বাটন ফিল্টারিং হ্যান্ডলার ------------------
    @bot.message_handler(func=lambda message: message.text == 'কাজ')
    def handle_task(message):
        if is_banned(message.from_user.id) or not check_membership(bot, message.from_user.id): return
        
        ig_active = is_task_type_active('Instagram')
        fb_active = is_task_type_active('Facebook')

        if not ig_active and not fb_active:
            bot.send_message(message.chat.id, "<b>বর্তমানে কোনো কাজ চালু নেই।</b>", parse_mode="HTML", reply_markup=main_menu(message.from_user.id))
            return

        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        
        if ig_active:
            markup.add(KeyboardButton('ইন্সটাগ্রাম কাজ', style="success", icon_custom_emoji_id="5364310996179503764"))
        if fb_active:
            markup.add(KeyboardButton('ফেসবুক কাজ', style="success", icon_custom_emoji_id="5389064576333527180"))
            
        markup.add(KeyboardButton('বাতিল', style="success", icon_custom_emoji_id="6206110936789423908"))
        
        task_text = (
            '<tg-emoji emoji-id="6082511510406436819">⚡️</tg-emoji>'
            '<b>যেকোনো একটি কাজ সিলেক্ট করুন</b>'
            '<tg-emoji emoji-id="6156513311585211842">⏬</tg-emoji>'
        )
        bot.send_message(message.chat.id, task_text, parse_mode="HTML", reply_markup=markup)

    # ------------------ ইন্সটাগ্রাম কাজ শুরু ------------------
    @bot.message_handler(func=lambda message: message.text == 'ইন্সটাগ্রাম কাজ')
    def start_instagram_task_auto(message):
        if is_banned(message.from_user.id): return
        if not is_task_type_active('Instagram'):
            bot.send_message(message.chat.id, "<b>বর্তমানে ইন্সটাগ্রাম কাজ বন্ধ আছে।</b>", parse_mode="HTML", reply_markup=main_menu(message.from_user.id))
            return

        current_price = get_setting('price') or 2.70
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add(KeyboardButton(f'ইন্সটাগ্রাম 2fa (৳{current_price:.2f})', style="success", icon_custom_emoji_id="5364310996179503764"))
        markup.add(KeyboardButton('বাতিল', style="success", icon_custom_emoji_id="6206110936789423908"))
        
        select_text = '<tg-emoji emoji-id="5213240855892073022">💠</tg-emoji><b>সিলেক্ট করুন:</b>'
        bot.send_message(message.chat.id, select_text, parse_mode="HTML", reply_markup=markup)

    @bot.message_handler(func=lambda message: message.text.startswith('ইন্সটাগ্রাম 2fa'))
    def process_auto_credential_delivery(message):
        if is_banned(message.from_user.id): return
        if not is_task_type_active('Instagram'):
            bot.send_message(message.chat.id, "<b>বর্তমানে ইন্সটাগ্রাম কাজ বন্ধ আছে।</b>", parse_mode="HTML", reply_markup=main_menu(message.from_user.id))
            return
        
        generated_username = generate_uncommon_username()
        admin_live_password = get_setting('password') or 'kamrol@22'
        
        task_instruction = (
            f'<tg-emoji emoji-id="6307777408300753473">👤</tg-emoji><b>Username:</b> <code>{generated_username}</code>\n'
            f'<tg-emoji emoji-id="5429405838345265327">🔓</tg-emoji><b>Password:</b> <code>{admin_live_password}</code>\n\n'
            f'<tg-emoji emoji-id="5364310996179503764">📱</tg-emoji><b>উপরের ইউজারনেম এবং পাসওয়ার্ড দিয়ে অ্যাকাউন্ট খুলুন। তারপর নিচে 2FA Set বাটনে ক্লিক করুন</b><tg-emoji emoji-id="5210956306952758910">😄</tg-emoji>'
        )
        
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add(KeyboardButton('2FA Set', style="success", icon_custom_emoji_id="5197288647275071607"))
        markup.add(KeyboardButton('কিভাবে কাজ করব', style="success", icon_custom_emoji_id="5798678738384195183"))
        markup.add(KeyboardButton('বাতিল', style="success", icon_custom_emoji_id="6206110936789423908"))
        
        bot.send_message(message.chat.id, task_instruction, parse_mode="HTML", reply_markup=markup)

    @bot.message_handler(func=lambda message: message.text == '2FA Set')
    def trigger_2fa_input_handler(message):
        if is_banned(message.from_user.id): return
        
        g_user = generate_uncommon_username()
        g_pass = get_setting('password') or "kamrol@22"
        
        twofa_prompt_text = (
            '<tg-emoji emoji-id="6176966310920983412">🔑</tg-emoji>'
            '<b>2FA Key টি দিন:</b>'
            '<tg-emoji emoji-id="5197474438970363734">⤵️</tg-emoji>'
        )
        
        msg = bot.send_message(message.chat.id, twofa_prompt_text, parse_mode="HTML", reply_markup=cancel_keyboard())
        bot.register_next_step_handler(msg, validate_and_generate_otp, g_user, g_pass)

    def validate_and_generate_otp(message, g_user, g_pass):
        if message.text == 'বাতিল':
            bot.clear_step_handler_by_chat_id(message.chat.id)
            bot.send_message(message.chat.id, "<b>কাজ বাতিল করা হয়েছে।</b>", parse_mode="HTML", reply_markup=main_menu(message.from_user.id))
            return
            
        raw_2fa = message.text.strip().replace(" ", "")
        
        if len(raw_2fa) != 32 or not raw_2fa.isupper() or not re.match(r"^[A-Z2-7]+$", raw_2fa):
            msg = bot.send_message(message.chat.id, "<b>দুঃখিত, এটি কোনো সঠিক 2FA Key নয়!</b>", parse_mode="HTML", reply_markup=cancel_keyboard())
            bot.register_next_step_handler(msg, validate_and_generate_otp, g_user, g_pass)
            return

        # ⚡ [Fast Index Check] ১ মিলিসেকেন্ডে ডুপ্লিকেট কি চেক করবে
        existing_task = tasks_col.find_one({'2fa_key': raw_2fa}, {'_id': 1})
        if existing_task:
            msg = bot.send_message(message.chat.id, "<b>এই 2FA Key টি ইতিমধ্যে ব্যবহার করা হয়েছে! অনুগ্রহ করে নতুন 2FA Key দিন:</b>", parse_mode="HTML", reply_markup=cancel_keyboard())
            bot.register_next_step_handler(msg, validate_and_generate_otp, g_user, g_pass)
            return

        try:
            totp = pyotp.TOTP(raw_2fa)
            current_otp = totp.now()
            
            success_text = (
                "<b>অ্যাকাউন্ট খোলা শেষ হলে নিচের বাটনে চাপ দিন:</b>\n"
                "<b>নিচের কোডটির ওপর চাপ দিলে অটোমেটিক কপি হয়ে যাবে</b> <tg-emoji emoji-id=\"5197474438970363734\">⤵️</tg-emoji>\n\n"
                f"🔑 <code>{current_otp}</code>"
            )
            
            finish_markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
            finish_markup.add(KeyboardButton('অ্যাকাউন্ট খোলা শেষ', style="success", icon_custom_emoji_id="6253780692908378898"))
            finish_markup.add(KeyboardButton('বাতিল', style="success", icon_custom_emoji_id="6206110936789423908"))
            
            bot.send_message(message.chat.id, success_text, parse_mode="HTML")
            msg = bot.send_message(message.chat.id, "<b>কাজ শেষ হলে নিচের বাটনে ক্লিক করুন:</b>", parse_mode="HTML", reply_markup=finish_markup)
            
            bot.register_next_step_handler(msg, handle_final_task_submission_step, g_user, g_pass, raw_2fa)
            
        except Exception as e:
            msg = bot.send_message(message.chat.id, "<b>দুঃখিত, এটি কোনো সঠিক 2FA Key নয়!</b>", parse_mode="HTML", reply_markup=cancel_keyboard())
            bot.register_next_step_handler(msg, validate_and_generate_otp, g_user, g_pass)

    def handle_final_task_submission_step(message, g_user, g_pass, raw_2fa):
        if message.text == 'বাতিল':
            bot.clear_step_handler_by_chat_id(message.chat.id)
            bot.send_message(message.chat.id, "<b>কাজ বাতিল করা হয়েছে।</b>", parse_mode="HTML", reply_markup=main_menu(message.from_user.id))
            return
            
        if message.text == 'অ্যাকাউন্ট খোলা শেষ':
            user_id = message.from_user.id
            
            tasks_col.insert_one({
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
            bot.send_message(message.chat.id, payment_notice, parse_mode="HTML", reply_markup=main_menu(user_id))
            
            group_task_text = (
                "<b>নতুন কাজ জমা হয়েছে!</b>\n\n"
                f"<b>Type:</b> Instagram\n"
                f"<b>User ID:</b> <code>{user_id}</code>\n"
                f"<b>Name:</b> {message.from_user.first_name}\n"
                f"<b>Username:</b> <code>{g_user}</code>"
            )
            try:
                bot.send_message(config.TASK_LOG_GROUP_ID, group_task_text, parse_mode="HTML")
            except Exception as e:
                print(f"Task Group Log Error: {e}")
        else:
            bot.send_message(message.chat.id, "<b>অনুগ্রহ করে নিচের 'অ্যাকাউন্ট খোলা শেষ' বাটনে ক্লিক করুন।</b>", parse_mode="HTML", reply_markup=main_menu(message.from_user.id))

    # ------------------ ফেসবুক কাজ শুরু ------------------
    @bot.message_handler(func=lambda message: message.text == 'ফেসবুক কাজ')
    def handle_facebook_task(message):
        if is_banned(message.from_user.id): return
        if not is_task_type_active('Facebook'):
            bot.send_message(message.chat.id, "<b>বর্তমানে ফেসবুক কাজ বন্ধ আছে।</b>", parse_mode="HTML", reply_markup=main_menu(message.from_user.id))
            return

        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add(KeyboardButton('Anymail/Number', style="success", icon_custom_emoji_id="6079925910029472766"))
        markup.add(KeyboardButton('বাতিল', style="success", icon_custom_emoji_id="4958526153955476488"))
        
        select_text = '<tg-emoji emoji-id="5213240855892073022">💠</tg-emoji> <b>সিলেক্ট করুন:</b>'
        bot.send_message(message.chat.id, select_text, parse_mode="HTML", reply_markup=markup)

    @bot.message_handler(func=lambda message: message.text == 'Anymail/Number')
    def handle_anymail_number(message):
        if is_banned(message.from_user.id): return
        if not is_task_type_active('Facebook'):
            bot.send_message(message.chat.id, "<b>বর্তমানে ফেসবুক কাজ বন্ধ আছে।</b>", parse_mode="HTML", reply_markup=main_menu(message.from_user.id))
            return

        fb_price = get_setting('fb_price') or 0.00
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add(KeyboardButton(f'0 fnd cookies | {fb_price:.2f}৳', style="success", icon_custom_emoji_id="5389064576333527180"))
        markup.add(KeyboardButton('বাতিল', style="success", icon_custom_emoji_id="4958526153955476488"))
        
        select_text = '<tg-emoji emoji-id="5213240855892073022">💠</tg-emoji> <b>সিলেক্ট করুন:</b>'
        bot.send_message(message.chat.id, select_text, parse_mode="HTML", reply_markup=markup)

    @bot.message_handler(func=lambda message: message.text.startswith('0 fnd cookies'))
    def process_facebook_credentials(message):
        if is_banned(message.from_user.id): return
        if not is_task_type_active('Facebook'):
            bot.send_message(message.chat.id, "<b>বর্তমানে ফেসবুক কাজ বন্ধ আছে।</b>", parse_mode="HTML", reply_markup=main_menu(message.from_user.id))
            return
        
        fname = generate_first_name() if callable(generate_first_name) else "First"
        lname = generate_last_name() if callable(generate_last_name) else "Last"
        admin_fb_pass = get_setting('fb_password') or get_setting('password') or 'kamrol@22'
        
        info_text = (
            f'<tg-emoji emoji-id="5352861489541714456">👤</tg-emoji> <b>First name:</b> <code>{fname}</code>\n'
            f'<tg-emoji emoji-id="5352861489541714456">👤</tg-emoji> <b>Last name:</b> <code>{lname}</code>\n'
            f'<tg-emoji emoji-id="5429405838345265327">🔑</tg-emoji> <b>Password:</b> <code>{admin_fb_pass}</code>\n\n'
            f'<tg-emoji emoji-id="5188344996356448758">📱</tg-emoji> <b>উপরের তথ্য দিয়ে অ্যাকাউন্ট খুলে নিচে Send UID বাটনে চাপ দিন</b> <tg-emoji emoji-id="5456258317477230911">👇</tg-emoji>'
        )
        
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add(KeyboardButton('Send UID', style="success", icon_custom_emoji_id="6338853910458930994"))
        markup.add(KeyboardButton('কিভাবে কাজ করব', style="success", icon_custom_emoji_id="5328222365971141647"))
        markup.add(KeyboardButton('বাতিল', style="success", icon_custom_emoji_id="4958526153955476488"))
        
        bot.send_message(message.chat.id, info_text, parse_mode="HTML", reply_markup=markup)

    @bot.message_handler(func=lambda message: message.text == 'Send UID')
    def prompt_facebook_uid(message):
        if is_banned(message.from_user.id): return
        
        prompt_text = (
            '<b>আপনার</b> <tg-emoji emoji-id="5389064576333527180">🆔</tg-emoji> '
            '<b>Facebook UID দিন:</b>'
        )
        
        cancel_markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        cancel_markup.add(KeyboardButton('বাতিল', style="success", icon_custom_emoji_id="4958526153955476488"))
        
        msg = bot.send_message(message.chat.id, prompt_text, parse_mode="HTML", reply_markup=cancel_markup)
        bot.register_next_step_handler(msg, validate_facebook_uid)

    def validate_facebook_uid(message):
        if message.text == 'বাতিল':
            bot.clear_step_handler_by_chat_id(message.chat.id)
            bot.send_message(message.chat.id, "<b>কাজ বাতিল করা হয়েছে।</b>", parse_mode="HTML", reply_markup=main_menu(message.from_user.id))
            return
            
        uid = message.text.strip()
        
        if len(uid) < 14 or not uid.isdigit():
            prompt_err = '<tg-emoji emoji-id="4958526153955476488">⚠️</tg-emoji> <b>দয়া করে আপনি আপনার সঠিক UID সেন্ড করুন:</b>'
            cancel_markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
            cancel_markup.add(KeyboardButton('বাতিল', style="success", icon_custom_emoji_id="4958526153955476488"))
            
            msg = bot.send_message(message.chat.id, prompt_err, parse_mode="HTML", reply_markup=cancel_markup)
            bot.register_next_step_handler(msg, validate_facebook_uid)
            return

        # ⚡ [Fast Index Check] fast UID lookup
        existing_uid = tasks_col.find_one({'fb_uid': uid}, {'_id': 1})
        if existing_uid:
            dup_err = f'<b>দুঃখিত আপনি এই UID একবার সেন্ট করেছেন দ্বিতীয়বার নেওয়া যাবে না</b> <tg-emoji emoji-id="4958526153955476488">❌</tg-emoji>'
            cancel_markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
            cancel_markup.add(KeyboardButton('বাতিল', style="success", icon_custom_emoji_id="4958526153955476488"))
            
            msg = bot.send_message(message.chat.id, dup_err, parse_mode="HTML", reply_markup=cancel_markup)
            bot.register_next_step_handler(msg, validate_facebook_uid)
            return

        cookie_prompt = '<b>আপনার Cookie দিন</b> <tg-emoji emoji-id="5197474438970363734">⤵️</tg-emoji>'
        cancel_markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        cancel_markup.add(KeyboardButton('বাতিল', style="success", icon_custom_emoji_id="4958526153955476488"))
        
        msg = bot.send_message(message.chat.id, cookie_prompt, parse_mode="HTML", reply_markup=cancel_markup)
        bot.register_next_step_handler(msg, collect_facebook_cookie, uid)

    def collect_facebook_cookie(message, fb_uid):
        if message.text == 'বাতিল':
            bot.clear_step_handler_by_chat_id(message.chat.id)
            bot.send_message(message.chat.id, "<b>কাজ বাতিল করা হয়েছে।</b>", parse_mode="HTML", reply_markup=main_menu(message.from_user.id))
            return

        cookie_text = message.text.strip()
        
        finish_prompt = '<tg-emoji emoji-id="6298612102709909362">⚙️</tg-emoji> <b>সম্পূর্ণ করতে নিচের বাটনে চাপুন:</b>'
        finish_markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        finish_markup.add(KeyboardButton('অ্যাকাউন্ট খোলা শেষ', style="success", icon_custom_emoji_id="6253780692908378898"))
        finish_markup.add(KeyboardButton('বাতিল', style="success", icon_custom_emoji_id="4958526153955476488"))
        
        msg = bot.send_message(message.chat.id, finish_prompt, parse_mode="HTML", reply_markup=finish_markup)
        bot.register_next_step_handler(msg, finalize_facebook_submission, fb_uid, cookie_text)

    def finalize_facebook_submission(message, fb_uid, fb_cookie):
        if message.text == 'বাতিল':
            bot.clear_step_handler_by_chat_id(message.chat.id)
            bot.send_message(message.chat.id, "<b>কাজ বাতিল করা হয়েছে।</b>", parse_mode="HTML", reply_markup=main_menu(message.from_user.id))
            return

        if message.text == 'অ্যাকাউন্ট খোলা শেষ':
            user_id = message.from_user.id
            
            tasks_col.insert_one({
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
            bot.send_message(message.chat.id, success_notice, parse_mode="HTML", reply_markup=main_menu(user_id))
            
            group_task_text = (
                "<b>নতুন ফেসবুক কাজ জমা হয়েছে!</b>\n\n"
                f"<b>Type:</b> Facebook\n"
                f"<b>User ID:</b> <code>{user_id}</code>\n"
                f"<b>FB UID:</b> <code>{fb_uid}</code>"
            )
            try:
                bot.send_message(config.TASK_LOG_GROUP_ID, group_task_text, parse_mode="HTML")
            except Exception as e:
                print(f"Task Group Log Error: {e}")
        else:
            bot.send_message(message.chat.id, "<b>অনুগ্রহ করে নিচের 'অ্যাকাউন্ট খোলা শেষ' বাটনে ক্লিক করুন।</b>", parse_mode="HTML", reply_markup=main_menu(message.from_user.id))

    # ------------------ ভিডিও গাইড ------------------
    @bot.message_handler(func=lambda message: message.text == 'কিভাবে কাজ করব')
    def send_video_guide(message):
        if is_banned(message.from_user.id): return
        video_url = get_setting('video_link')
        if not video_url or not str(video_url).startswith(('http://', 'https://')):
            video_url = 'https://youtube.com'
            
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("ভিডিওটি দেখুন", url=video_url))
        bot.send_message(message.chat.id, "<b>কাজের নিয়ম দেখার জন্য নিচের ভিডিও বাটনে ক্লিক করুন:</b>", parse_mode="HTML", reply_markup=markup)
