from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import config
from database import is_banned, get_setting
from startHandler import check_membership

def register(bot):
    # 🛠️ 'সাপোর্ট' বাটন ফিল্টার
    @bot.message_handler(func=lambda message: message.text in ['সাপোর্ট', '🎧 সাপোর্ট'])
    def handle_support(message):
        if is_banned(message.from_user.id) or not check_membership(bot, message.from_user.id): return
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("📢 আমাদের অফিশিয়াল চ্যানেল", url=config.SUPPORT_CHANNEL_LINK))
        bot.send_message(
            message.chat.id, 
            f"🎧 <b>গ্রাহক সেবা কেন্দ্র</b>\n\nকোনো সমস্যা বা জিজ্ঞাসার জন্য আমাদের সাপোর্ট চ্যানেলে যুক্ত হোন:\n\n🔗 {config.SUPPORT_CHANNEL_LINK}\n\n⚠️ <b>নোট:</b> অযথা মেসেজ দেওয়া থেকে বিরত থাকুন। ধন্যবাদ!", 
            parse_mode="HTML", 
            reply_markup=markup
        )

    # 🛠️ 'আমি নতুন' বাটন ফিল্টার (সাথে URL ভ্যালিডেশন)
    @bot.message_handler(func=lambda message: message.text in ['আমি নতুন', '🆕 আমি নতুন ❓'])
    def handle_new_user_guide(message):
        if is_banned(message.from_user.id) or not check_membership(bot, message.from_user.id): return
        
        video_url = get_setting('video_link')
        
        # লিংক যদি ভুল থাকে বা 'http' দিয়ে শুরু না হয়, তবে ডিফল্ট লিংক বসবে
        if not video_url or not str(video_url).startswith(('http://', 'https://')):
            video_url = 'https://youtube.com'
            
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🎥 ভিডিওটি দেখুন", url=video_url))
        bot.send_message(
            message.chat.id, 
            "🆕 <b>কিভাবে কাজ করবেন গাইডলাইন?</b>\n\nনিচের বাটনে ক্লিক করে কাজের সম্পূর্ণ ভিডিওটি দেখে নিন।", 
            parse_mode="HTML", 
            reply_markup=markup
        )
