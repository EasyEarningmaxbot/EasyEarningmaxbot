from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import config
from database import get_setting, is_task_type_active

def main_menu(user_id=None):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton('ব্যালেন্স', style="success", icon_custom_emoji_id="6298412618658879257"), 
        KeyboardButton('কাজ', style="success", icon_custom_emoji_id="5197269100878907942")
    )
    markup.add(
        KeyboardButton('উত্তোলনের অনুরোধ', style="success", icon_custom_emoji_id="6190336264940559752"), 
        KeyboardButton('সাপোর্ট', style="success", icon_custom_emoji_id="5253742260054409879")
    )
    markup.add(
        KeyboardButton('আমার রেফারেল', style="success", icon_custom_emoji_id="6206027872121918710"), 
        KeyboardButton('আমি নতুন', style="success", icon_custom_emoji_id="5217449524410199951")
    )
    
    # 🏆 লিডারবোর্ড অন থাকলেই কেবল মেম্বারদের বাটন দেখাবে
    is_lb_active = get_setting('leaderboard_active')
    if is_lb_active is None or is_lb_active == True:
        markup.add(
            KeyboardButton('লিডারবোর্ড', style="success", icon_custom_emoji_id="6194737030165959506")
        )

    if user_id and user_id in config.ADMIN_IDS:
        markup.add(KeyboardButton('অ্যাডমিন প্যানেল', style="success", icon_custom_emoji_id="6206220960966646470"))
    return markup

# 💰 মেম্বারদের জন্য উইথড্র চ্যানেল/মেনু (ডায়নামিক অন/অফ এবং লিমিট সহ)
def withdraw_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    
    # লিমিটসমূহ রিড করা
    usdt_limit = get_setting('min_withdraw_usdt') or 25.00
    bkash_limit = get_setting('min_withdraw_bkash') or 100.00
    nagad_limit = get_setting('min_withdraw_nagad') or 100.00
    recharge_limit = get_setting('min_withdraw_recharge') or 20.00

    # অন/অফ স্ট্যাটাস চেক (ডিফল্ট True বা Active থাকবে)
    usdt_active = get_setting('status_usdt') if get_setting('status_usdt') is not None else True
    bkash_active = get_setting('status_bkash') if get_setting('status_bkash') is not None else True
    nagad_active = get_setting('status_nagad') if get_setting('status_nagad') is not None else True
    recharge_active = get_setting('status_recharge') if get_setting('status_recharge') is not None else True

    # মেথড ON থাকলেই কেবল বাটন যুক্ত হবে
    if usdt_active:
        markup.add(KeyboardButton(f'USDT (BEP-20) -> সর্বনিম্ন {usdt_limit:.1f}(~0.05)', style="success", icon_custom_emoji_id="5348212415077064131"))
    if bkash_active:
        markup.add(KeyboardButton(f'বিকাশ -> সর্বনিম্ন {int(bkash_limit)}৳(~৫)', style="success", icon_custom_emoji_id="5348469219761626211"))
    if nagad_active:
        markup.add(KeyboardButton(f'নগদ -> সর্বনিম্ন {int(nagad_limit)}৳(~৫)', style="success", icon_custom_emoji_id="5352985330628730418"))
    if recharge_active:
        markup.add(KeyboardButton(f'মোবাইল রিচার্জ -> সর্বনিম্ন {int(recharge_limit)}৳', style="success", icon_custom_emoji_id="5337132498965010628"))

    markup.add(KeyboardButton('বাতিল', style="success", icon_custom_emoji_id="6206110936789423908"))
    return markup

def admin_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton('রিপোর্ট', style="success", icon_custom_emoji_id="6206515969385308049"), 
        KeyboardButton('টাস্ক সেটিংস', style="success", icon_custom_emoji_id="5341715473882955310")
    )
    markup.add(
        KeyboardButton('ইউজার ও টাকা', style="success", icon_custom_emoji_id="6221736233970700254"), 
        KeyboardButton('অন্যান্য', style="success", icon_custom_emoji_id="4956619819836244992")
    )
    markup.add(KeyboardButton('প্রধান মেনু', style="success", icon_custom_emoji_id="6206505206197261313"))
    return markup

def reports_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton('টাস্ক রিপোর্ট (Excel)', style="success", icon_custom_emoji_id="6046627337821231012"), 
        KeyboardButton('রিপোর্ট সাবমিট', style="success", icon_custom_emoji_id="5449442513616121857")
    )
    markup.add(KeyboardButton('অ্যাডমিন প্যানেল', style="success", icon_custom_emoji_id="6206505206197261313"))
    return markup

def user_money_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton('উত্তোলন রিভিউ', style="success", icon_custom_emoji_id="6190336264940559752"), 
        KeyboardButton('ব্যালেন্স অ্যাড/রিমুভ', style="success", icon_custom_emoji_id="6298412618658879257")
    )
    markup.add(
        KeyboardButton('কাজের মূল্য সেট', style="success", icon_custom_emoji_id="5197269100878907942"), 
        KeyboardButton('রেফারেল কমিশন', style="success", icon_custom_emoji_id="6206027872121918710")
    )
    markup.add(
        KeyboardButton('উত্তোলন লিমিট', style="success", icon_custom_emoji_id="6190336264940559752"), 
        KeyboardButton('উত্তোলন মেথড On/Off', style="success", icon_custom_emoji_id="6206108815075579644")
    )
    markup.add(KeyboardButton('অ্যাডমিন প্যানেল', style="success", icon_custom_emoji_id="6206505206197261313"))
    return markup

def task_settings_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton('ব্যান / আনব্যান', style="success", icon_custom_emoji_id="6206110936789423908"), 
        KeyboardButton('কাজ On/Off', style="success", icon_custom_emoji_id="6206108815075579644")
    )
    markup.add(
        KeyboardButton('কাজের ভিডিও সেট', style="success", icon_custom_emoji_id="6228824441837587879"),
        KeyboardButton('সব পেন্ডিং কাজ রিমুভ', style="success", icon_custom_emoji_id="6224185666704511761")
    )
    markup.add(KeyboardButton('অ্যাডমিন প্যানেল', style="success", icon_custom_emoji_id="6206505206197261313"))
    return markup

# ⚙️ আলাদা কাজ ON/OFF করার সাব-মেনু
def task_on_off_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    
    ig_status = "ON 🟢" if is_task_type_active('Instagram') else "OFF 🔴"
    fb_status = "ON 🟢" if is_task_type_active('Facebook') else "OFF 🔴"
    
    markup.add(
        KeyboardButton(f"📱 ইন্সটাগ্রাম 2FA [{ig_status}]", style="success", icon_custom_emoji_id="5197269100878907942"),
        KeyboardButton(f"📘 0 fnd cookies [{fb_status}]", style="success", icon_custom_emoji_id="5197269100878907942"),
        KeyboardButton('অ্যাডমিন প্যানেল', style="success", icon_custom_emoji_id="6206505206197261313")
    )
    return markup

def others_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton('এনাউন্সমেন্ট', style="success", icon_custom_emoji_id="6206080502651164081"), 
        KeyboardButton('পাসওয়ার্ড সেট', style="success", icon_custom_emoji_id="5337255927735163754")
    )
    markup.add(
        KeyboardButton('লিডার বোর্ড ON OF', style="success", icon_custom_emoji_id="6194737030165959506"),
        KeyboardButton('লিডার বোর্ড প্রাইস সেট', style="success", icon_custom_emoji_id="6194737030165959506")
    )
    markup.add(KeyboardButton('অ্যাডমিন প্যানেল', style="success", icon_custom_emoji_id="6206505206197261313"))
    return markup

def cancel_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    markup.add(KeyboardButton('বাতিল', style="success", icon_custom_emoji_id="6206110936789423908"))
    return markup
