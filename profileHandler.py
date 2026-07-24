import logging
import asyncio
from aiogram import Router, types, F, Bot

from database import is_banned, users_col, tasks_col
from startHandler import check_membership

# ১. Aiogram Router ইনিশিয়ালাইজেশন
router = Router()

# -------------------------------------------------------------
# 💳 'ব্যালেন্স' বাটন হ্যান্ডলার (Ultra-Fast & Asynchronous)
# -------------------------------------------------------------
@router.message(F.text.contains('ব্যালেন্স'))
async def handle_balance(message: types.Message, bot: Bot, state=None):
    try:
        user_id = message.from_user.id
        
        # FSM State বা স্টেপ ক্লিয়ার করা (যদি কোনো ফর্ম খোলা থাকে)
        if state:
            await state.clear()

        # ১. ব্যান চেক (অ্যাসিঙ্ক ডাটাবেস রিড)
        banned = await asyncio.to_thread(is_banned, user_id)
        if banned:
            return

        # ২. চ্যানেল মেম্বারশিপ চেক (অ্যাসিঙ্ক এপিআই কল)
        joined = await check_membership(bot, user_id)
        if not joined:
            return

        # ⚡ ৩. সমান্তরালে (Parallel) ডাটাবেস থেকে ইউজার ডাটা এবং পেন্ডিং কাজ ফেচ করা (Ultra High Speed Optimization)
        def fetch_user_and_tasks():
            user_data = users_col.find_one({'user_id': user_id})
            
            if not user_data:
                # ইউজার না থাকলে নতুন ডিফল্ট ডাটা আপসার্ট করা
                users_col.update_one(
                    {'user_id': user_id}, 
                    {'$set': {
                        'balance': 0.00, 
                        'pending_withdraw': 0.00, 
                        'total_income': 0.00, 
                        'completed_tasks': 0
                    }}, 
                    upsert=True
                )
                user_data = users_col.find_one({'user_id': user_id})

            pending_count = tasks_col.count_documents({
                'user_id': user_id, 
                'status': 'Pending Review'
            })
            
            return user_data, pending_count

        # ব্যাকগ্রাউন্ড থ্রেডে ডাটা ফেচ করা
        user, pending_review = await asyncio.to_thread(fetch_user_and_tasks)

        # ৪. তথ্যগুলো ভেরিয়েবলে সেট করা
        current_balance = user.get('balance', 0.00) if user else 0.00
        pending_withdraw = user.get('pending_withdraw', 0.00) if user else 0.00
        total_income = user.get('total_income', 0.00) if user else 0.00
        completed_tasks = user.get('completed_tasks', 0) if user else 0
        
        # 💬 ৫. ব্যালেন্স মেসেজ ফরম্যাট
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
        
        # 🚀 ৬. ফাস্ট মেসেজ সেন্ড
        await message.answer(balance_text)

    except Exception as e:
        logging.error(f"Error in handle_balance: {e}", exc_info=True)
