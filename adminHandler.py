import io
import openpyxl
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import config
from database import (
    users_col, tasks_col, withdrawals_col, get_setting, update_setting, 
    update_balance, set_banned, is_task_type_active, toggle_task_type_status
)
from keyboards import (
    admin_menu, main_menu, cancel_keyboard, 
    reports_menu, user_money_menu, task_settings_menu, task_on_off_menu, others_menu
)

def register(bot):
    @bot.message_handler(func=lambda message: message.text in ['অ্যাডমিন প্যানেল'])
    def handle_admin_panel(message):
        if message.from_user.id in config.ADMIN_IDS:
            bot.send_message(message.chat.id, "অ্যাডমিন প্যানেলে স্বাগতম!", reply_markup=admin_menu())
        else:
            bot.send_message(message.chat.id, "অনুমতি নেই।")

    # ================= ৪টি ক্যাটাগরি সাব-মেনু ওপেন করার হ্যান্ডলার =================
    @bot.message_handler(func=lambda message: message.text == 'রিপোর্ট' and message.from_user.id in config.ADMIN_IDS)
    def handle_reports_category(message):
        bot.send_message(message.chat.id, "<b>Reports Panel</b>", parse_mode="HTML", reply_markup=reports_menu())

    @bot.message_handler(func=lambda message: message.text == 'ইউজার ও টাকা' and message.from_user.id in config.ADMIN_IDS)
    def handle_user_money_category(message):
        bot.send_message(message.chat.id, "<b>ইউজার ও টাকা সেটিংস</b>", parse_mode="HTML", reply_markup=user_money_menu())

    @bot.message_handler(func=lambda message: message.text == 'টাস্ক সেটিংস' and message.from_user.id in config.ADMIN_IDS)
    def handle_task_settings_category(message):
        bot.send_message(message.chat.id, "<b>টাস্ক সেটিংস</b>", parse_mode="HTML", reply_markup=task_settings_menu())

    @bot.message_handler(func=lambda message: message.text == 'অন্যান্য' and message.from_user.id in config.ADMIN_IDS)
    def handle_others_category(message):
        bot.send_message(message.chat.id, "<b>অন্যান্য সেটিংস</b>", parse_mode="HTML", reply_markup=others_menu())

    @bot.message_handler(func=lambda message: message.text == 'প্রধান মেনু')
    def back_to_main_menu(message):
        bot.send_message(message.chat.id, "প্রধান মেনুতে ফিরে যাচ্ছি...", reply_markup=main_menu(message.from_user.id))

    # ================= ১. টাস্ক রিপোর্ট (Excel Export) =================
    @bot.message_handler(func=lambda message: message.text == 'টাস্ক রিপোর্ট (Excel)' and message.from_user.id in config.ADMIN_IDS)
    def download_tasks_menu(message):
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add(
            KeyboardButton('📥 IG 2FA [Excel Report]', style="success", icon_custom_emoji_id="5364310996179503764"),
            KeyboardButton('📥 FB Cookies [Excel Report]', style="success", icon_custom_emoji_id="5389064576333527180"),
            KeyboardButton('অ্যাডমিন প্যানেল', style="success", icon_custom_emoji_id="6206505206197261313")
        )
        bot.send_message(message.chat.id, "<b>কোন টাস্কের এক্সেল ফাইল নামাতে চান সিলেক্ট করুন:</b>", parse_mode="HTML", reply_markup=markup)

    @bot.message_handler(func=lambda message: message.text == '📥 IG 2FA [Excel Report]' and message.from_user.id in config.ADMIN_IDS)
    def export_instagram_excel(message):
        pending_tasks = list(tasks_col.find({
            '$or': [{'type': 'Instagram'}, {'type': {'$exists': False}}], 
            'status': 'Pending Review',
            'username': {'$exists': True, '$ne': ''}
        }))
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Instagram Tasks"
        ws.append(['Username', 'Password', '2FA Key'])
        
        valid_tasks = [t for t in pending_tasks if t.get('username')]
        
        if not valid_tasks:
            ws.append(['No data', 'No data', 'No data'])
        else:
            for task in valid_tasks:
                ws.append([task.get('username', ''), task.get('password', ''), task.get('2fa_key', '')])
                
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        bot.send_document(message.chat.id, ('Instagram_Task_Report.xlsx', output.getvalue()), caption="<b>ইন্সটাগ্রাম কাজের পেন্ডিং Excel ফাইল।</b>", parse_mode="HTML", reply_markup=reports_menu())

    @bot.message_handler(func=lambda message: message.text == '📥 FB Cookies [Excel Report]' and message.from_user.id in config.ADMIN_IDS)
    def export_facebook_excel(message):
        pending_tasks = list(tasks_col.find({
            'type': 'Facebook', 
            'status': 'Pending Review',
            'fb_uid': {'$exists': True, '$ne': ''}
        }))
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Facebook Tasks"
        ws.append(['UID', 'Password', 'Cookies'])
        
        default_fb_pass = get_setting('fb_password') or get_setting('password') or 'kamrol@22'
        valid_tasks = [t for t in pending_tasks if t.get('fb_uid')]
        
        if not valid_tasks:
            ws.append(['No data', 'No data', 'No data'])
        else:
            for task in valid_tasks:
                ws.append([task.get('fb_uid', ''), task.get('password', default_fb_pass), task.get('fb_cookie', '')])
                
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        bot.send_document(message.chat.id, ('Facebook_Task_Report.xlsx', output.getvalue()), caption="<b>ফেসবুক কাজের পেন্ডিং Excel ফাইল।</b>", parse_mode="HTML", reply_markup=reports_menu())


    # ================= ২. রিপোর্ট সাবমিট (Excel Import Accept/Reject) =================
    @bot.message_handler(func=lambda message: message.text == 'রিপোর্ট সাবমিট' and message.from_user.id in config.ADMIN_IDS)
    def report_submit_menu(message):
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add(
            KeyboardButton('📤 FB Cookies [Submit Report]', style="success", icon_custom_emoji_id="5389064576333527180"),
            KeyboardButton('📤 IG 2FA [Submit Report]', style="success", icon_custom_emoji_id="5364310996179503764"),
            KeyboardButton('অ্যাডমিন প্যানেল', style="success", icon_custom_emoji_id="6206505206197261313")
        )
        bot.send_message(message.chat.id, "<b>রিপোর্ট সাবমিট এর জন্য টাস্ক নির্বাচন করুন:</b>", parse_mode="HTML", reply_markup=markup)

    @bot.message_handler(func=lambda message: message.text in ['📤 FB Cookies [Submit Report]', '📤 IG 2FA [Submit Report]'] and message.from_user.id in config.ADMIN_IDS)
    def submit_action_choice(message):
        task_type = 'Facebook' if 'FB' in message.text else 'Instagram'
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        
        if task_type == 'Facebook':
            accept_btn = KeyboardButton('FB Accept Tasks', style="success")
            reject_btn = KeyboardButton('FB Reject Tasks', style="success")
        else:
            accept_btn = KeyboardButton('IG Accept Tasks', style="success")
            reject_btn = KeyboardButton('IG Reject Tasks', style="success")
            
        markup.add(accept_btn, reject_btn)
        markup.add(KeyboardButton('অ্যাডমিন প্যানেল', style="success", icon_custom_emoji_id="6206505206197261313"))
        bot.send_message(message.chat.id, f"<b>{message.text}</b> এর জন্য অপশন নির্বাচন করুন:", parse_mode="HTML", reply_markup=markup)

    # FB Action Triggers
    @bot.message_handler(func=lambda message: message.text in ['FB Accept Tasks', 'FB Reject Tasks'] and message.from_user.id in config.ADMIN_IDS)
    def trigger_fb_file_input(message):
        action = 'accept' if 'Accept' in message.text else 'reject'
        
        if action == 'accept':
            msg_text = (
                '<tg-emoji emoji-id="6298612102709909362">⚙️</tg-emoji> '
                '<tg-emoji emoji-id="5389064576333527180">📘</tg-emoji> '
                '<b>Facebook (Number) — Accept করতে .xlsx ফাইল পাঠান।</b>\n\n'
                'Format: (Column A: UID)\n'
                '(exported file থেকে first column select করে upload করো, header row থাকবে)'
            )
        else:
            msg_text = (
                '<tg-emoji emoji-id="6302916351430235741">❌</tg-emoji> '
                '<tg-emoji emoji-id="5389064576333527180">📘</tg-emoji> '
                '<b>Facebook (Number) — Reject করতে .xlsx ফাইল পাঠান।</b>\n\n'
                'Format: (Column A: UID)\n'
                '(exported file থেকে first column select করে upload করো, header row থাকবে)'
            )
            
        msg = bot.send_message(message.chat.id, msg_text, parse_mode="HTML", reply_markup=cancel_keyboard())
        bot.register_next_step_handler(msg, process_facebook_excel_file, action)

    def process_facebook_excel_file(message, action):
        if message.text == 'বাতিল':
            bot.clear_step_handler_by_chat_id(message.chat.id)
            bot.send_message(message.chat.id, "বাতিল করা হয়েছে।", reply_markup=reports_menu())
            return

        if not message.document:
            msg = bot.send_message(message.chat.id, "<b>অনুগ্রহ করে একটি সঠিক .xlsx ফাইল আপলোড করুন!</b>", parse_mode="HTML", reply_markup=cancel_keyboard())
            bot.register_next_step_handler(msg, process_facebook_excel_file, action)
            return

        try:
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            wb = openpyxl.load_workbook(io.BytesIO(downloaded_file))
            sheet = wb.active
            
            uids = []
            for row in sheet.iter_rows(min_row=2, values_only=True): 
                if row and row[0]:
                    uids.append(str(row[0]).strip())

            fb_price = get_setting('fb_price') or 0.00
            ref_percent = get_setting('ref_commission') or 10

            user_summary = {} 
            processed_count = 0

            for uid in uids:
                task = tasks_col.find_one({'fb_uid': uid, 'type': 'Facebook', 'status': 'Pending Review'})
                if task:
                    w_id = task['user_id']
                    user_summary[w_id] = user_summary.get(w_id, 0) + 1
                    tasks_col.delete_one({'_id': task['_id']})
                    processed_count += 1

            for worker_id, count in user_summary.items():
                total_earned = count * fb_price
                
                if action == 'accept':
                    update_balance(worker_id, total_earned)
                    users_col.update_one(
                        {'user_id': worker_id}, 
                        {'$inc': {'total_income': total_earned, 'completed_tasks': count}}
                    )
                    
                    user_msg = (
                        f'<tg-emoji emoji-id="6253780692908378898">🎉</tg-emoji> '
                        f'<b>অভিনন্দন আপনার কাজটা এপ্রুভ করা হয়েছে এবং আপনি কাজের জন্য ({total_earned:.2f})টাকা পেয়েছেন</b> '
                        f'<tg-emoji emoji-id="5389064576333527180">📘</tg-emoji>'
                    )
                    try: bot.send_message(worker_id, user_msg, parse_mode="HTML")
                    except: pass

                    user_data = users_col.find_one({'user_id': worker_id})
                    referrer_id = user_data.get('referrer_id') if user_data else None
                    if referrer_id:
                        comm_amount = total_earned * (ref_percent / 100.0)
                        if comm_amount > 0:
                            update_balance(referrer_id, comm_amount)
                            users_col.update_one({'user_id': referrer_id}, {'$inc': {'total_income': comm_amount, 'ref_income': comm_amount}})
                            
                            ref_msg = (
                                f'<tg-emoji emoji-id="6125457176161948466">🎁</tg-emoji> '
                                f'<b>আপনার রেফার থেকে আপনি {comm_amount:.2f} টাকা পেয়েছেন অভিনন্দন আপনি আরো রেফার করুন</b> '
                                f'<tg-emoji emoji-id="5417924076503062111">🚀</tg-emoji>'
                            )
                            try: bot.send_message(referrer_id, ref_msg, parse_mode="HTML")
                            except: pass
                
                elif action == 'reject':
                    user_msg = (
                        f'<tg-emoji emoji-id="6302916351430235741">❌</tg-emoji> '
                        f'<b>সরি ভাইয়া আপনার এই {count} টা একাউন্ট ব্যান হয়ে গিয়েছে বায়ার নেয় নাই এটার জন্য আপনি কোন পেমেন্ট পাবেন না</b> '
                        f'<tg-emoji emoji-id="5389064576333527180">📘</tg-emoji>'
                    )
                    try: bot.send_message(worker_id, user_msg, parse_mode="HTML")
                    except: pass

            bot.send_message(message.chat.id, f"<b>ফেসবুক ফাইল প্রসেস সম্পন্ন!</b>\nমোট আইটেম প্রসেসড: {processed_count}", parse_mode="HTML", reply_markup=reports_menu())

        except Exception as e:
            bot.send_message(message.chat.id, f"<b>ফাইল প্রসেস করতে সমস্যা হয়েছে! Error: {e}</b>", parse_mode="HTML", reply_markup=reports_menu())


    # IG Action Triggers
    @bot.message_handler(func=lambda message: message.text in ['IG Accept Tasks', 'IG Reject Tasks'] and message.from_user.id in config.ADMIN_IDS)
    def trigger_ig_file_input(message):
        action = 'accept' if 'Accept' in message.text else 'reject'
        
        if action == 'accept':
            msg_text = (
                '<tg-emoji emoji-id="6255771332940663641">✨</tg-emoji> '
                '<tg-emoji emoji-id="5364310996179503764">📱</tg-emoji> '
                '<b>Instagram 2FA — Accept করতে .xlsx ফাইল পাঠান।</b>\n\n'
                'Format: (Column A: Username)\n'
                '(exported file থেকে first column select করে upload করো, header row থাকবে)'
            )
        else:
            msg_text = (
                '<tg-emoji emoji-id="6224185666704511761">❌</tg-emoji> '
                '<tg-emoji emoji-id="5364310996179503764">📱</tg-emoji> '
                '<b>Instagram 2FA — Reject করতে .xlsx ফাইল পাঠান।</b>\n\n'
                'Format: (Column A: Username)\n'
                '(exported file থেকে first column select করে upload করো, header row থাকবে)'
            )
            
        msg = bot.send_message(message.chat.id, msg_text, parse_mode="HTML", reply_markup=cancel_keyboard())
        bot.register_next_step_handler(msg, process_instagram_excel_file, action)

    def process_instagram_excel_file(message, action):
        if message.text == 'বাতিল':
            bot.clear_step_handler_by_chat_id(message.chat.id)
            bot.send_message(message.chat.id, "বাতিল করা হয়েছে।", reply_markup=reports_menu())
            return

        if not message.document:
            msg = bot.send_message(message.chat.id, "<b>অনুগ্রহ করে একটি সঠিক .xlsx ফাইল আপলোড করুন!</b>", parse_mode="HTML", reply_markup=cancel_keyboard())
            bot.register_next_step_handler(msg, process_instagram_excel_file, action)
            return

        try:
            file_info = bot.get_file(message.document.file_id)
            downloaded_file = bot.download_file(file_info.file_path)
            
            wb = openpyxl.load_workbook(io.BytesIO(downloaded_file))
            sheet = wb.active
            
            usernames = []
            for row in sheet.iter_rows(min_row=2, values_only=True): 
                if row and row[0]:
                    usernames.append(str(row[0]).strip())

            ig_price = get_setting('price') or 2.70
            ref_percent = get_setting('ref_commission') or 10

            user_summary = {} 
            processed_count = 0

            for uname in usernames:
                task = tasks_col.find_one({'username': uname, 'status': 'Pending Review'})
                if task:
                    w_id = task['user_id']
                    user_summary[w_id] = user_summary.get(w_id, 0) + 1
                    tasks_col.delete_one({'_id': task['_id']})
                    processed_count += 1

            for worker_id, count in user_summary.items():
                total_earned = count * ig_price
                
                if action == 'accept':
                    update_balance(worker_id, total_earned)
                    users_col.update_one(
                        {'user_id': worker_id}, 
                        {'$inc': {'total_income': total_earned, 'completed_tasks': count}}
                    )
                    
                    user_msg = (
                        f'<tg-emoji emoji-id="6253780692908378898">🎉</tg-emoji> '
                        f'<b>বস কি খেলা দেখাইলা তোমার কাজ এপ্রোভ হয়েছে তোমার ব্যালেন্সে {total_earned:.2f} টাকা এড করা হয়েছে,</b> '
                        f'<tg-emoji emoji-id="5364310996179503764">📱</tg-emoji>'
                    )
                    try: bot.send_message(worker_id, user_msg, parse_mode="HTML")
                    except: pass

                    user_data = users_col.find_one({'user_id': worker_id})
                    referrer_id = user_data.get('referrer_id') if user_data else None
                    if referrer_id:
                        comm_amount = total_earned * (ref_percent / 100.0)
                        if comm_amount > 0:
                            update_balance(referrer_id, comm_amount)
                            users_col.update_one({'user_id': referrer_id}, {'$inc': {'total_income': comm_amount, 'ref_income': comm_amount}})
                            
                            ref_msg = (
                                f'<tg-emoji emoji-id="6125457176161948466">🎁</tg-emoji> '
                                f'<b>আপনার রেফার থেকে আপনি {comm_amount:.2f} টাকা পেয়েছেন অভিনন্দন আপনি আরো রেফার করুন</b> '
                                f'<tg-emoji emoji-id="5417924076503062111">🚀</tg-emoji>'
                            )
                            try: bot.send_message(referrer_id, ref_msg, parse_mode="HTML")
                            except: pass
                
                elif action == 'reject':
                    user_msg = (
                        f'<tg-emoji emoji-id="6224185666704511761">❌</tg-emoji> '
                        f'<b>দুঃখিত আপনি এই অ্যাকাউন্ট খোলার জন্য পেমেন্ট পাবেন না কারণ আপনাদের একাউন্টগুলা বেন হয়ে গেছে</b> '
                        f'<tg-emoji emoji-id="5364310996179503764">📱</tg-emoji>'
                    )
                    try: bot.send_message(worker_id, user_msg, parse_mode="HTML")
                    except: pass

            bot.send_message(message.chat.id, f"<b>ইন্সটাগ্রাম ফাইল প্রসেস সম্পন্ন!</b>\nমোট আইটেম প্রসেসড: {processed_count}", parse_mode="HTML", reply_markup=reports_menu())

        except Exception as e:
            bot.send_message(message.chat.id, f"<b>ফাইল প্রসেস করতে সমস্যা হয়েছে! Error: {e}</b>", parse_mode="HTML", reply_markup=reports_menu())


    # ================= সব পেন্ডিং কাজ রিমুভ হ্যান্ডলার =================
    @bot.message_handler(func=lambda message: message.text == 'সব পেন্ডিং কাজ রিমুভ' and message.from_user.id in config.ADMIN_IDS)
    def prompt_delete_all_pending_tasks(message):
        pending_count = tasks_col.count_documents({'status': 'Pending Review'})
        
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            KeyboardButton('হ্যাঁ, ডিলিট করুন', style="success"),
            KeyboardButton('বাতিল', style="success", icon_custom_emoji_id="6206110936789423908")
        )
        
        text = (
            f'<b>সতর্কতা!</b>\n\n'
            f'বর্তমানে মোট <b>{pending_count}টি</b> পেন্ডিং কাজ রিভিউ তালিকায় রয়েছে।\n'
            f'আপনি কি নিশ্চিত যে রিভিউতে থাকা <b>সব কাজ ডাটাবেজ থেকে মুছে ফেলতে চান?</b>'
        )
        msg = bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)
        bot.register_next_step_handler(msg, process_delete_all_pending_tasks)

    def process_delete_all_pending_tasks(message):
        if message.text == 'হ্যাঁ, ডিলিট করুন':
            result = tasks_col.delete_many({'status': 'Pending Review'})
            deleted_count = result.deleted_count
            bot.send_message(
                message.chat.id, 
                f"<b>সফলভাবে রিভিউতে থাকা সকল ({deleted_count}টি) কাজ ডাটাবেজ থেকে মুছে ফেলা হয়েছে!</b>", 
                parse_mode="HTML", 
                reply_markup=task_settings_menu()
            )
        else:
            bot.clear_step_handler_by_chat_id(message.chat.id)
            bot.send_message(message.chat.id, "বাতিল করা হয়েছে।", reply_markup=task_settings_menu())


    # ================= ৩. পাসওয়ার্ড সেট (ইন্সটাগ্রাম ও ফেসবুক) =================
    @bot.message_handler(func=lambda message: message.text == 'পাসওয়ার্ড সেট' and message.from_user.id in config.ADMIN_IDS)
    def set_task_password_menu(message):
        prompt_text = (
            '<tg-emoji emoji-id="5429405838345265327">🔑</tg-emoji> '
            '<b>কোন টাস্কের পাসওয়ার্ড সেট করতে চান</b> '
            '<tg-emoji emoji-id="5197474438970363734">⤵️</tg-emoji>'
        )
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add(
            KeyboardButton('Instagram 2FA Password', style="success", icon_custom_emoji_id="5364310996179503764"),
            KeyboardButton('Anymail/Number Password', style="success", icon_custom_emoji_id="5389064576333527180"),
            KeyboardButton('অ্যাডমিন প্যানেল', style="success", icon_custom_emoji_id="6206505206197261313")
        )
        bot.send_message(message.chat.id, prompt_text, parse_mode="HTML", reply_markup=markup)

    @bot.message_handler(func=lambda message: message.text in ['Instagram 2FA Password', 'Anymail/Number Password'] and message.from_user.id in config.ADMIN_IDS)
    def prompt_pass_change(message):
        is_fb = ('Anymail' in message.text)
        setting_key = 'fb_password' if is_fb else 'password'
        curr_pass = get_setting(setting_key) or 'kamrol@22'
        
        if is_fb:
            msg_text = (
                f'<tg-emoji emoji-id="5389064576333527180">📘</tg-emoji> '
                f'<b>Facebook (Number) বর্তমান পাসওয়ার্ড</b> <tg-emoji emoji-id="5429405838345265327">🔑</tg-emoji>: <code>{curr_pass}</code>\n'
                f'<b>নতুন পাসওয়ার্ড দিন:</b>'
            )
        else:
            msg_text = (
                f'<tg-emoji emoji-id="5364310996179503764">📱</tg-emoji> '
                f'<b>Instagram বর্তমান পাসওয়ার্ড</b> <tg-emoji emoji-id="5429405838345265327">🔑</tg-emoji>: <code>{curr_pass}</code>\n'
                f'<b>নতুন পাসওয়ার্ড দিন:</b>'
            )
            
        msg = bot.send_message(message.chat.id, msg_text, parse_mode="HTML", reply_markup=cancel_keyboard())
        bot.register_next_step_handler(msg, process_save_pass, setting_key)

    def process_save_pass(message, setting_key):
        if message.text == 'বাতিল':
            bot.clear_step_handler_by_chat_id(message.chat.id)
            bot.send_message(message.chat.id, "বাতিল করা হয়েছে।", reply_markup=others_menu())
            return
        new_pass = message.text.strip()
        update_setting(setting_key, new_pass)
        bot.send_message(message.chat.id, f"পাসওয়ার্ড সফলভাবে আপডেট করা হয়েছে: <code>{new_pass}</code>", parse_mode="HTML", reply_markup=others_menu())


    # ================= ৪. কাজের মূল্য সেট =================
    @bot.message_handler(func=lambda message: message.text == 'কাজের মূল্য সেট' and message.from_user.id in config.ADMIN_IDS)
    def set_task_price_menu(message):
        prompt_text = (
            '<tg-emoji emoji-id="5364310996179503764">📱</tg-emoji>'
            '<tg-emoji emoji-id="5389064576333527180">📘</tg-emoji>'
            '<b>কোন কাজের মূল্য সেট করতে চান তা সিলেক্ট করুন</b> '
            '<tg-emoji emoji-id="5197474438970363734">⤵️</tg-emoji>'
        )
        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add(
            KeyboardButton('IG কাজের মূল্য সেট', style="success", icon_custom_emoji_id="5364310996179503764"),
            KeyboardButton('FB কাজের মূল্য সেট', style="success", icon_custom_emoji_id="5389064576333527180"),
            KeyboardButton('অ্যাডমিন প্যানেল', style="success", icon_custom_emoji_id="6206505206197261313")
        )
        bot.send_message(message.chat.id, prompt_text, parse_mode="HTML", reply_markup=markup)

    @bot.message_handler(func=lambda message: ('IG কাজের মূল্য সেট' in message.text or 'FB কাজের মূল্য সেট' in message.text) and message.from_user.id in config.ADMIN_IDS)
    def prompt_price_change(message):
        is_fb = ('FB' in message.text)
        setting_key = 'fb_price' if is_fb else 'price'
        curr_price = get_setting(setting_key) or 0.00
        
        msg_text = (
            f'<b>বর্তমান মূল্য আছে {curr_price:.2f}৳। আপনার নতুন মূল্যটি নিচে লিখে দিন</b> '
            f'<tg-emoji emoji-id="5197474438970363734">⤵️</tg-emoji>'
        )
        msg = bot.send_message(message.chat.id, msg_text, parse_mode="HTML", reply_markup=cancel_keyboard())
        bot.register_next_step_handler(msg, process_save_price, setting_key)

    def process_save_price(message, setting_key):
        if message.text == 'বাতিল':
            bot.clear_step_handler_by_chat_id(message.chat.id)
            bot.send_message(message.chat.id, "বাতিল করা হয়েছে।", reply_markup=user_money_menu())
            return
        try:
            new_price = float(message.text.strip())
            update_setting(setting_key, new_price)
            
            success_text = (
                '<b>অভিনন্দন! আপনার মূল্যটি চেঞ্জ করা হয়েছে</b> '
                '<tg-emoji emoji-id="6253780692908378898">🎉</tg-emoji>'
            )
            bot.send_message(message.chat.id, success_text, parse_mode="HTML", reply_markup=user_money_menu())
        except ValueError:
            bot.send_message(message.chat.id, "<b>সঠিক সংখ্যা দিয়ে মূল্য পুনরায় চেষ্টা করুন।</b>", parse_mode="HTML", reply_markup=user_money_menu())


    # ================= ৫. লিডারবোর্ড কন্ট্রোল (ON/OFF ও প্রাইজ সেট) =================
    @bot.message_handler(func=lambda message: message.text == 'লিডার বোর্ড ON OF' and message.from_user.id in config.ADMIN_IDS)
    def toggle_leaderboard(message):
        current_status = get_setting('leaderboard_active')
        if current_status is None:
            current_status = True  # ডিফল্ট অন
            
        new_status = not current_status
        update_setting('leaderboard_active', new_status)
        
        if new_status:
            text = '<tg-emoji emoji-id="5213240855892073022">📍</tg-emoji> <b>লিডার বোর্ড এই মুহূর্তে ON করা হলো,</b>'
        else:
            text = '<tg-emoji emoji-id="5213240855892073022">📍</tg-emoji> <b>লিডার বোর্ড এই মুহূর্তে OFF করা হলো</b>'
            
        bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=others_menu())

    @bot.message_handler(func=lambda message: message.text == 'লিডার বোর্ড প্রাইস সেট' and message.from_user.id in config.ADMIN_IDS)
    def set_leaderboard_prizes_prompt(message):
        curr_prizes = get_setting('leaderboard_prizes') or "100,50,30,20,10"
        
        text = (
            f'<tg-emoji emoji-id="4956418939920843885">🎁</tg-emoji> <b>টপ ৫ র‍্যাংকের জন্য reward amount (৳) লিখুন, কমা দিয়ে আলাদা করে (rank1,rank2,rank3,rank4,rank5):</b>\n\n'
            f'<b>বর্তমান:</b> {curr_prizes}'
        )
        msg = bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=cancel_keyboard())
        bot.register_next_step_handler(msg, process_save_leaderboard_prizes)

    def process_save_leaderboard_prizes(message):
        if message.text == 'বাতিল':
            bot.clear_step_handler_by_chat_id(message.chat.id)
            bot.send_message(message.chat.id, "বাতিল করা হয়েছে।", reply_markup=others_menu())
            return
            
        raw_text = message.text.strip().strip(',')
        p_list = [p.strip() for p in raw_text.split(',') if p.strip()]
        
        if len(p_list) == 5:
            try:
                _ = [float(p) for p in p_list]
                clean_prize_str = ",".join(p_list)
                update_setting('leaderboard_prizes', clean_prize_str)
                bot.send_message(message.chat.id, f"<b>লিডারবোর্ড প্রাইজ সফলভাবে আপডেট হয়েছে!</b>\n<b>বর্তমান প্রাইজ:</b> {clean_prize_str}", parse_mode="HTML", reply_markup=others_menu())
            except ValueError:
                bot.send_message(message.chat.id, "<b>ভুল ইনপুট! শুধু সংখ্যা ও কমা ব্যবহার করুন। (যেমন: 500,240,200,100,50)</b>", parse_mode="HTML", reply_markup=others_menu())
        else:
            bot.send_message(message.chat.id, "<b>অবশ্যই ৫ জন র‍্যাংকের জন্য কমা দিয়ে আলাদা করে অ্যামাউন্ট লিখুন।</b>", parse_mode="HTML", reply_markup=others_menu())


    # ================= অন্যান্য সাধারণ ফাংশন =================
    @bot.message_handler(func=lambda message: message.text == 'এনাউন্সমেন্ট' and message.from_user.id in config.ADMIN_IDS)
    def admin_announcement(message):
        msg = bot.send_message(message.chat.id, "বটের সকল মেম্বারদের কাছে যে অফিশিয়াল নোটিশটি পাঠাতে চান, তা এখানে সুন্দর করে টাইপ করে দিন:", reply_markup=cancel_keyboard())
        bot.register_next_step_handler(msg, process_announcement)

    def process_announcement(message):
        if message.text == 'বাতিল':
            bot.clear_step_handler_by_chat_id(message.chat.id)
            bot.send_message(message.chat.id, "এনাউন্সমেন্ট বাতিল করা হয়েছে।", reply_markup=others_menu())
            return
            
        announcement_text = message.text
        all_users = list(users_col.find({}, {'user_id': 1}))
        success_count = 0
        
        bot.send_message(message.chat.id, f"এনাউন্সমেন্ট পাঠানো শুরু হয়েছে... (মোট ইউজার: {len(all_users)} জন)", reply_markup=others_menu())
        
        for u in all_users:
            try: 
                bot.send_message(u['user_id'], f"<b>অফিশিয়াল ঘোষণা:</b>\n\n{announcement_text}", parse_mode="HTML")
                success_count += 1
            except: 
                pass
                
        bot.send_message(message.chat.id, f"নোটিশ পাঠানো সফল হয়েছে!\nমোট {success_count} জন সচল মেম্বার ইনবক্সে মেসেজটি পেয়েছে।", reply_markup=others_menu())

    @bot.message_handler(func=lambda message: message.text == 'উত্তোলন রিভিউ' and message.from_user.id in config.ADMIN_IDS)
    def view_withdraw_requests(message):
        pending = list(withdrawals_col.find({'status': 'Pending'}))
        if not pending:
            bot.send_message(message.chat.id, "কোনো পেন্ডিং উইথড্র রিকোয়েস্ট নেই।")
            return
        for w in pending[:5]:
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("Approve", callback_data=f"gr_wd_approve_{w['_id']}"), InlineKeyboardButton("Reject", callback_data=f"gr_wd_reject_{w['_id']}"))
            text = f"<b>উইথড্র রিকোয়েস্ট রিভিউ (বক্স):</b>\nইউজার: {w['first_name']}\nমেথড: {w['method']}\nনম্বর: {w['number']}\nপরিমাণ: ৳{w['amount']:.2f}"
            bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)

    @bot.message_handler(func=lambda message: message.text == 'ব্যান / আনব্যান' and message.from_user.id in config.ADMIN_IDS)
    def ban_unban_user(message):
        msg = bot.send_message(message.chat.id, "ব্যান বা আনব্যান করতে ইউজারের ID দিন:", reply_markup=cancel_keyboard())
        bot.register_next_step_handler(msg, process_ban_unban)

    def process_ban_unban(message):
        if message.text == 'বাতিল':
            bot.clear_step_handler_by_chat_id(message.chat.id)
            bot.send_message(message.chat.id, "বাতিল করা হয়েছে।", reply_markup=task_settings_menu())
            return
        try:
            target_id = int(message.text.strip())
            user = users_col.find_one({'user_id': target_id})
            if not user: return
            new_status = not user.get('is_banned', False)
            set_banned(target_id, new_status)
            bot.send_message(message.chat.id, f"ইউজার {target_id} এর স্ট্যাটাস আপডেট সফল!", reply_markup=task_settings_menu())
        except: pass

    @bot.message_handler(func=lambda message: message.text == 'ব্যালেন্স অ্যাড/রিমুভ' and message.from_user.id in config.ADMIN_IDS)
    def balance_add_remove(message):
        msg = bot.send_message(message.chat.id, "ইউজারের Telegram ID দিন:", reply_markup=cancel_keyboard())
        bot.register_next_step_handler(msg, process_bal_change_id)

    def process_bal_change_id(message):
        if message.text == 'বাতিল':
            bot.clear_step_handler_by_chat_id(message.chat.id)
            bot.send_message(message.chat.id, "বাতিল করা হয়েছে।", reply_markup=user_money_menu())
            return
        try:
            t_id = int(message.text.strip())
            msg = bot.send_message(message.chat.id, "টাকার পরিমাণ লিখুন (কেটে নিতে মাইনাস সহ):", reply_markup=cancel_keyboard())
            bot.register_next_step_handler(msg, process_bal_change_amount, t_id)
        except: pass

    def process_bal_change_amount(message, t_id):
        if message.text == 'বাতিল':
            bot.clear_step_handler_by_chat_id(message.chat.id)
            bot.send_message(message.chat.id, "বাতিল করা হয়েছে।", reply_markup=user_money_menu())
            return
        try:
            val = float(message.text)
            update_balance(t_id, val)
            if val > 0:
                users_col.update_one({'user_id': t_id}, {'$inc': {'total_income': val}})
            bot.send_message(message.chat.id, f"ব্যালেন্স সফলভাবে আপডেট করা হয়েছে।", reply_markup=user_money_menu())
        except: pass

    # ================= কাজ ON / OFF হ্যান্ডলার =================
    @bot.message_handler(func=lambda message: message.text == 'কাজ On/Off' and message.from_user.id in config.ADMIN_IDS)
    def open_task_on_off_menu(message):
        bot.send_message(
            message.chat.id, 
            "<b>যেই কাজটি অন বা অফ করতে চান সেটির ওপর ক্লিক করুন:</b>", 
            parse_mode="HTML", 
            reply_markup=task_on_off_menu()
        )

    @bot.message_handler(func=lambda message: ('ইন্সটাগ্রাম 2FA' in message.text or '0 fnd cookies' in message.text) and message.from_user.id in config.ADMIN_IDS)
    def toggle_specific_task_status(message):
        task_type = 'Instagram' if 'ইন্সটাগ্রাম' in message.text else 'Facebook'
        new_status = toggle_task_type_status(task_type)
        status_text = "ON" if new_status else "OFF"
        
        bot.send_message(
            message.chat.id, 
            f"<b>{task_type} কাজ এখন [{status_text}] করা হয়েছে।</b>", 
            parse_mode="HTML", 
            reply_markup=task_on_off_menu()
        )

    # ================= উত্তোলন মেথড ON / OFF হ্যান্ডলার =================
    @bot.message_handler(func=lambda message: message.text in ['উত্তোলনের মেথড On/Off', 'উত্তোলন মেথড On/Off'] and message.from_user.id in config.ADMIN_IDS)
    def handle_withdraw_toggle_menu(message):
        show_toggle_keyboard(message.chat.id)

    def show_toggle_keyboard(chat_id):
        bkash_status = get_setting('status_bkash') if get_setting('status_bkash') is not None else True
        nagad_status = get_setting('status_nagad') if get_setting('status_nagad') is not None else True
        recharge_status = get_setting('status_recharge') if get_setting('status_recharge') is not None else True
        usdt_status = get_setting('status_usdt') if get_setting('status_usdt') is not None else True

        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton(f"বিকাশ: {'ON' if bkash_status else 'OFF'}", callback_data="toggle_wd_bkash"))
        markup.add(InlineKeyboardButton(f"নগদ: {'ON' if nagad_status else 'OFF'}", callback_data="toggle_wd_nagad"))
        markup.add(InlineKeyboardButton(f"মোবাইল রিচার্জ: {'ON' if recharge_status else 'OFF'}", callback_data="toggle_wd_recharge"))
        markup.add(InlineKeyboardButton(f"USDT (BEP-20): {'ON' if usdt_status else 'OFF'}", callback_data="toggle_wd_usdt"))

        bot.send_message(chat_id, "<b>উত্তোলন মেথড অন/অফ কন্ট্রোল প্যানেল:</b>\nনিচের বাটনে ক্লিক করে অন বা অফ করুন।", parse_mode="HTML", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith('toggle_wd_'))
    def handle_withdraw_toggle_callback(call):
        if call.from_user.id not in config.ADMIN_IDS: return
        
        method = call.data.split('_')[2] # bkash / nagad / recharge / usdt
        key = f'status_{method}'
        
        current_status = get_setting(key) if get_setting(key) is not None else True
        new_status = not current_status
        
        update_setting(key, new_status)
        
        status_text = "চালু (ON)" if new_status else "বন্ধ (OFF)"
        bot.answer_callback_query(call.id, f"{method.upper()} মেথডটি {status_text} করা হয়েছে!", show_alert=True)
        
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        show_toggle_keyboard(call.message.chat.id)

    # ================= ডায়নামিক উত্তোলন লিমিট সেট হ্যান্ডলার =================
    @bot.message_handler(func=lambda message: message.text in ['উত্তোলনের লিমিট', 'উত্তোলন লিমিট'] and message.from_user.id in config.ADMIN_IDS)
    def withdraw_limit_menu(message):
        usdt_limit = get_setting('min_withdraw_usdt') or 25.00
        bkash_limit = get_setting('min_withdraw_bkash') or 100.00
        nagad_limit = get_setting('min_withdraw_nagad') or 100.00
        recharge_limit = get_setting('min_withdraw_recharge') or 20.00

        markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
        markup.add(
            KeyboardButton(f'USDT (BEP-20) -> লিমিট {usdt_limit:.2f}(~0.05)', style="success", icon_custom_emoji_id="5348212415077064131"),
            KeyboardButton(f'বিকাশ -> লিমিট {bkash_limit:.2f}৳(~৫)', style="success", icon_custom_emoji_id="5348469219761626211"),
            KeyboardButton(f'নগদ -> লিমিট {nagad_limit:.2f}৳(~৫)', style="success", icon_custom_emoji_id="5352985330628730418"),
            KeyboardButton(f'মোবাইল রিচার্জ -> লিমিট {recharge_limit:.2f}৳', style="success", icon_custom_emoji_id="5337132498965010628"),
            KeyboardButton('অ্যাডমিন প্যানেল', style="success", icon_custom_emoji_id="6206505206197261313")
        )
        bot.send_message(message.chat.id, "<b>কোন মেথডের উত্তোলন লিমিট পরিবর্তন করতে চান সিলেক্ট করুন:</b>", parse_mode="HTML", reply_markup=markup)

    @bot.message_handler(func=lambda message: ('USDT (BEP-20)' in message.text or 'বিকাশ' in message.text or 'নগদ' in message.text or 'মোবাইল রিচার্জ' in message.text) and message.from_user.id in config.ADMIN_IDS)
    def prompt_method_limit_change(message):
        text = message.text
        if 'USDT' in text:
            method_key = 'min_withdraw_usdt'
            curr_limit = get_setting(method_key) or 25.00
            prompt_text = (
                f'<tg-emoji emoji-id="6221736233970700254">💳</tg-emoji> '
                f'বর্তমানে সর্বনিম্ন সেট করা আছে ({curr_limit:.2f}) নতুন সর্বনিম্ন উত্তোলন সেট করতে হলে নিচে লিখুন '
                f'<tg-emoji emoji-id="6222141833502266367">⤵️</tg-emoji>'
            )
        elif 'বিকাশ' in text:
            method_key = 'min_withdraw_bkash'
            curr_limit = get_setting(method_key) or 100.00
            prompt_text = (
                f'<tg-emoji emoji-id="6221736233970700254">💳</tg-emoji> '
                f'বর্তমানে সর্বনিম্ন সেট করা আছে ({curr_limit:.2f}) নতুন সর্বনিম্ন উত্তোলন সেট করতে হলে নিচে লিখুন '
                f'<tg-emoji emoji-id="6222141833502266367">⤵️</tg-emoji>'
            )
        elif 'নগদ' in text:
            method_key = 'min_withdraw_nagad'
            curr_limit = get_setting(method_key) or 100.00
            prompt_text = (
                f'<tg-emoji emoji-id="6221736233970700254">💳</tg-emoji> '
                f'বর্তমানে সর্বনিম্ন সেট করা আছে ({curr_limit:.2f}) নতুন সর্বনিম্ন উত্তোলন সেট করতে হলে নিচে লিখুন '
                f'<tg-emoji emoji-id="6222141833502266367">⤵️</tg-emoji>'
            )
        elif 'মোবাইল রিচার্জ' in text:
            method_key = 'min_withdraw_recharge'
            curr_limit = get_setting(method_key) or 20.00
            prompt_text = (
                f'<tg-emoji emoji-id="6221736233970700254">💳</tg-emoji> '
                f'বর্তমানে সর্বনিম্ন রিচার্জ {curr_limit:.2f}) সেট করা আছে নতুন কোনটা সেট করবেন সেটা লিখুন '
                f'<tg-emoji emoji-id="6222141833502266367">⤵️</tg-emoji>'
            )

        msg = bot.send_message(message.chat.id, prompt_text, parse_mode="HTML", reply_markup=cancel_keyboard())
        bot.register_next_step_handler(msg, process_save_method_limit, method_key)

    def process_save_method_limit(message, method_key):
        if message.text == 'বাতিল':
            bot.clear_step_handler_by_chat_id(message.chat.id)
            bot.send_message(message.chat.id, "বাতিল করা হয়েছে।", reply_markup=user_money_menu())
            return
        try:
            raw_input = message.text.replace(')', '').strip()
            new_limit = float(raw_input)
            update_setting(method_key, new_limit)
            bot.send_message(
                message.chat.id, 
                f"<b>উত্তোলন লিমিট সফলভাবে পরিবর্তন করা হয়েছে: ৳{new_limit:.2f}</b>", 
                parse_mode="HTML", 
                reply_markup=user_money_menu()
            )
        except ValueError:
            bot.send_message(
                message.chat.id, 
                "<b>ভুল ইনপুট! অনুগ্রহ করে সঠিক সংখ্যা দিয়ে পুনরায় চেষ্টা করুন।</b>", 
                parse_mode="HTML", 
                reply_markup=user_money_menu()
            )

    @bot.message_handler(func=lambda message: message.text == 'রেফারেল কমিশন' and message.from_user.id in config.ADMIN_IDS)
    def set_ref_commission(message):
        msg = bot.send_message(message.chat.id, "নতুন রেফারেল কমিশন (%) লিখুন:", reply_markup=cancel_keyboard())
        bot.register_next_step_handler(msg, lambda m: update_setting('ref_commission', int(m.text)) or bot.send_message(m.chat.id, "কমিশন আপডেট সফল!", reply_markup=user_money_menu()))

    @bot.message_handler(func=lambda message: message.text == 'কাজের ভিডিও সেট' and message.from_user.id in config.ADMIN_IDS)
    def set_video_guide(message):
        msg = bot.send_message(message.chat.id, "নতুন ভিডিও লিংক পেস্ট করুন:", reply_markup=cancel_keyboard())
        bot.register_next_step_handler(msg, lambda m: update_setting('video_link', m.text.strip()) or bot.send_message(m.chat.id, "ভিডিও লিংক আপডেট সফল!", reply_markup=task_settings_menu()))
