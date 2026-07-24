import asyncio
from aiogram.utils.keyboard import ReplyKeyboardBuilder, KeyboardButton, InlineKeyboardBuilder, InlineKeyboardButton
import config
from database import get_setting, is_task_type_active

# -------------------------------------------------------------
# 📌 ১. প্রধান মেনু (Main Menu)
# -------------------------------------------------------------
async def main_menu(user_id=None):
    builder = ReplyKeyboardBuilder()
    
    builder.row(
        KeyboardButton(text='ব্যালেন্স'), 
        KeyboardButton(text='কাজ')
    )
    builder.row(
        KeyboardButton(text='উত্তোলনের অনুরোধ'), 
        KeyboardButton(text='সাপোর্ট')
    )
    builder.row(
        KeyboardButton(text='আমার রেফারেল'), 
        KeyboardButton(text='আমি নতুন')
    )
    
    # 🏆 লিডারবোর্ড অন থাকলেই কেবল মেম্বারদের বাটন দেখাবে
    is_lb_active = await get_setting('leaderboard_active')
    if is_lb_active is None or is_lb_active is True:
        builder.row(KeyboardButton(text='লিডারবোর্ড'))

    if user_id and user_id in config.ADMIN_IDS:
        builder.row(KeyboardButton(text='অ্যাডমিন প্যানেল'))
        
    return builder.as_markup(resize_keyboard=True)

# -------------------------------------------------------------
# 💰 ২. উইথড্র মেনু (Withdraw Menu - Dynamic Limits)
# -------------------------------------------------------------
async def withdraw_menu():
    builder = ReplyKeyboardBuilder()
    
    # সমান্তরালে (Parallel) লিমিট ও স্ট্যাটাস রিড করা
    usdt_limit = await get_setting('min_withdraw_usdt') or 25.00
    bkash_limit = await get_setting('min_withdraw_bkash') or 100.00
    nagad_limit = await get_setting('min_withdraw_nagad') or 100.00
    recharge_limit = await get_setting('min_withdraw_recharge') or 20.00

    usdt_active = await get_setting('status_usdt')
    bkash_active = await get_setting('status_bkash')
    nagad_active = await get_setting('status_nagad')
    recharge_active = await get_setting('status_recharge')

    usdt_active = usdt_active if usdt_active is not None else True
    bkash_active = bkash_active if bkash_active is not None else True
    nagad_active = nagad_active if nagad_active is not None else True
    recharge_active = recharge_active if recharge_active is not None else True

    # মেথড ON থাকলেই কেবল বাটন যুক্ত হবে
    if usdt_active:
        builder.row(KeyboardButton(text=f'USDT (BEP-20) -> সর্বনিম্ন {usdt_limit:.1f}(~0.05)'))
    if bkash_active:
        builder.row(KeyboardButton(text=f'বিকাশ -> সর্বনিম্ন {int(bkash_limit)}৳(~৫)'))
    if nagad_active:
        builder.row(KeyboardButton(text=f'নগদ -> সর্বনিম্ন {int(nagad_limit)}৳(~৫)'))
    if recharge_active:
        builder.row(KeyboardButton(text=f'মোবাইল রিচার্জ -> সর্বনিম্ন {int(recharge_limit)}৳'))

    builder.row(KeyboardButton(text='বাতিল'))
    return builder.as_markup(resize_keyboard=True)

# -------------------------------------------------------------
# 🛠️ ৩. অ্যাডমিন প্যানেল ও সাব-মেনুসমূহ
# -------------------------------------------------------------
async def admin_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text='রিপোর্ট'), KeyboardButton(text='টাস্ক সেটিংস'))
    builder.row(KeyboardButton(text='ইউজার ও টাকা'), KeyboardButton(text='অন্যান্য'))
    builder.row(KeyboardButton(text='প্রধান মেনু'))
    return builder.as_markup(resize_keyboard=True)

async def reports_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text='টাস্ক রিপোর্ট (Excel)'), KeyboardButton(text='রিপোর্ট সাবমিট'))
    builder.row(KeyboardButton(text='অ্যাডমিন প্যানেল'))
    return builder.as_markup(resize_keyboard=True)

async def user_money_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text='উত্তোলন রিভিউ'), KeyboardButton(text='ব্যালেন্স অ্যাড/রিমুভ'))
    builder.row(KeyboardButton(text='কাজের মূল্য সেট'), KeyboardButton(text='রেফারেল কমিশন'))
    builder.row(KeyboardButton(text='উত্তোলন লিমিট'), KeyboardButton(text='উত্তোলন মেথড On/Off'))
    builder.row(KeyboardButton(text='অ্যাডমিন প্যানেল'))
    return builder.as_markup(resize_keyboard=True)

async def task_settings_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text='ব্যান / আনব্যান'), KeyboardButton(text='কাজ On/Off'))
    builder.row(KeyboardButton(text='কাজের ভিডিও সেট'), KeyboardButton(text='সব পেন্ডিং কাজ রিমুভ'))
    builder.row(KeyboardButton(text='অ্যাডমিন প্যানেল'))
    return builder.as_markup(resize_keyboard=True)

# ⚙️ আলাদা কাজ ON/OFF করার সাব-মেনু
async def task_on_off_menu():
    builder = ReplyKeyboardBuilder()
    
    ig_active = await is_task_type_active('Instagram')
    fb_active = await is_task_type_active('Facebook')
    
    ig_status = "ON 🟢" if ig_active else "OFF 🔴"
    fb_status = "ON 🟢" if fb_active else "OFF 🔴"
    
    builder.row(KeyboardButton(text=f"📱 ইন্সটাগ্রাম 2FA [{ig_status}]"))
    builder.row(KeyboardButton(text=f"📘 0 fnd cookies [{fb_status}]"))
    builder.row(KeyboardButton(text='অ্যাডমিন প্যানেল'))
    return builder.as_markup(resize_keyboard=True)

async def others_menu():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text='এনাউন্সমেন্ট'), KeyboardButton(text='পাসওয়ার্ড সেট'))
    builder.row(KeyboardButton(text='লিডার বোর্ড ON OF'), KeyboardButton(text='লিডার বোর্ড প্রাইস সেট'))
    builder.row(KeyboardButton(text='অ্যাডমিন প্যানেল'))
    return builder.as_markup(resize_keyboard=True)

async def cancel_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text='বাতিল'))
    return builder.as_markup(resize_keyboard=True)
