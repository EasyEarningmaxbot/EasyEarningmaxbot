from database import is_banned, users_col, get_setting
from startHandler import check_membership

def register(bot):
    @bot.message_handler(func=lambda message: message.text in ['আমার রেফারেল', '👥 আমার রেফারেল', '🎁 আমার রেফারেল'])
    def handle_referral(message):
        if is_banned(message.from_user.id) or not check_membership(bot, message.from_user.id): 
            return
            
        user_id = message.from_user.id
        
        # 🔗 ডায়নামিক বটের ইউজারনেম লিংক (অটোমেটিক বর্তমান বটের ইউজারনেম নিবে)
        try:
            bot_username = bot.get_me().username
        except Exception:
            bot_username = "EasyEarningmaxbot"  # ব্যাকআপ ফলব্যাক ইউজারনেম
            
        ref_link = f"https://t.me/{bot_username}?start={user_id}"
        
        ref_count = users_col.count_documents({'referrer_id': user_id})
        user_data = users_col.find_one({'user_id': user_id})
        ref_income = user_data.get('ref_income', 0.00) if user_data else 0.00
        commission = get_setting('ref_commission') or 10

        ref_text = (
            f'<tg-emoji emoji-id="6312317437840725952">🎁</tg-emoji> <b>আমার রেফারেল</b>\n'
            f'━━━━━━━━━━━━━━━━━━━━━━\n'
            f'<tg-emoji emoji-id="5352861489541714456">🎯</tg-emoji> <b>মোট রেফার:</b> {ref_count} জন\n'
            f'<tg-emoji emoji-id="6190336264940559752">💰</tg-emoji> <b>মোট রেফার ইনকাম:</b> {ref_income:.2f} BDT\n\n'
            f'<tg-emoji emoji-id="4958689671950369798">🔗</tg-emoji> <b>আপনার রেফার লিংক:</b>\n'
            f'<code>{ref_link}</code>\n\n'
            f'<tg-emoji emoji-id="5352980533150259581">📣</tg-emoji> <i>আপনার আমন্ত্রিত ব্যক্তি যা ইনকাম করবে, তার থেকে আপনি {commission}% কমিশন সরাসরি আপনার ব্যালেন্সে পেয়ে যাবেন।</i>'
        )

        bot.send_message(message.chat.id, ref_text, parse_mode="HTML")
