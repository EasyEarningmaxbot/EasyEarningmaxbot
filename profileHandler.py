from database import is_banned, users_col, tasks_col
from startHandler import check_membership

def register(bot):
    # 'ব্যালেন্স' বাটন হ্যান্ডলার
    @bot.message_handler(func=lambda message: message.text and 'ব্যালেন্স' in message.text)
    def handle_balance(message):
        try:
            user_id = message.from_user.id
            
            # স্টেপ হ্যান্ডলার ক্লিয়ার করা
            bot.clear_step_handler_by_chat_id(message.chat.id)

            # ব্যান এবং চ্যানেল মেম্বারশিপ চেক
            if is_banned(user_id) or not check_membership(bot, user_id): 
                return

            # ইউজার ডাটা চেক ও ডিফল্ট ডাটা সেট
            user = users_col.find_one({'user_id': user_id})
            if not user:
                users_col.update_one(
                    {'user_id': user_id}, 
                    {'$set': {'balance': 0.00, 'pending_withdraw': 0.00, 'total_income': 0.00, 'completed_tasks': 0}}, 
                    upsert=True
                )
                user = users_col.find_one({'user_id': user_id})

            current_balance = user.get('balance', 0.00) if user else 0.00
            pending_withdraw = user.get('pending_withdraw', 0.00) if user else 0.00
            total_income = user.get('total_income', 0.00) if user else 0.00
            
            # ✅ সমাধান: ইউজার প্রোফাইল থেকে এপ্রুভ হওয়া সফল কাজের সংখ্যা আনা হচ্ছে
            completed_tasks = user.get('completed_tasks', 0) if user else 0
            
            # পেন্ডিং কাজের হিসাব এখনও জমা থাকা tasks_col থেকেই চেক হবে
            pending_review = tasks_col.count_documents({'user_id': user_id, 'status': 'Pending Review'})
            
            # ব্যালেন্স মেসেজ ফরম্যাট
            balance_text = (
                '<tg-emoji emoji-id="5409048419211682843">💳</tg-emoji> <b>আপনার ব্যালেন্স</b>\n'
                '━━━━━━━━━━━━━━━━━━━━━━\n'
                f'<tg-emoji emoji-id="5447591434251158839">💰</tg-emoji> <b>ব্যালেন্স: {current_balance:.2f} BDT</b>\n'
                f'<tg-emoji emoji-id="6086980694460861135">⏳</tg-emoji> <b>উত্তোলন (পেন্ডিং): {pending_withdraw:.2f} BDT</b>\n'
                f'<tg-emoji emoji-id="6001434068435079689">💵</tg-emoji> <b>Total Income: {total_income:.2f} BDT</b>\n'
                '━━━━━━━━━━━━━━━━━━━━━━\n'
                f'<tg-emoji emoji-id="6084722370591853232">✅</tg-emoji> <b>সফল কাজ: {completed_tasks} টি</b>\n'
                f'<tg-emoji emoji-id="6084396322444544568">🔎</tg-emoji> <b>পেন্ডিং কাজ: {pending_review} টি</b>'
            )
            
            # মেসেজ সেন্ড
            bot.send_message(message.chat.id, balance_text, parse_mode="HTML")

        except Exception as e:
            print(f"Error in handle_balance: {e}")
