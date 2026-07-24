import time
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING

import config

# ================= MongoDB Async Client Setup =================
client = AsyncIOMotorClient(config.MONGO_URI)
db = client['easyincomedb']

users_col = db['users']
tasks_col = db['tasks']
withdrawals_col = db['withdrawals']
settings_col = db['settings']

# 🚀 [Performance Optimization] MongoDB Async Indexing
async def create_indexes():
    try:
        await users_col.create_index([("user_id", ASCENDING)], unique=True)
        await users_col.create_index([("completed_tasks", DESCENDING)])
        await tasks_col.create_index([("2fa_key", ASCENDING)])
        await tasks_col.create_index([("fb_uid", ASCENDING)])
        print("⚡ MongoDB successfully connected and Async Indexes Created!")
    except Exception as e:
        print(f"Error creating indexes: {e}")

# Default settings setup (অ্যাসিঙ্ক্রোনাস)
async def setup_default_settings():
    doc = await settings_col.find_one({'_id': 'task_settings'})
    if not doc:
        await settings_col.insert_one({
            '_id': 'task_settings',
            'is_active': True,
            'is_active_Instagram': True,
            'is_active_Facebook': True,
            'price': 2.70,
            'fb_price': 0.00,
            'password': 'kamrol@22',
            'fb_password': 'kamrol@22',
            'ref_commission': 10,
            'min_withdraw': 50.00,
            'min_withdraw_usdt': 25.00,
            'min_withdraw_bkash': 110.00,
            'min_withdraw_nagad': 10.00,
            'min_withdraw_recharge': 10.00,
            'usd_rate': 120.00,
            'video_link': 'https://youtube.com',
            'support_username': '@Kamrul_Owner',
            'leaderboard_active': True,
            'leaderboard_prizes': '100,50,30,20,10',
            'status_bkash': True,
            'status_nagad': True,
            'status_recharge': True,
            'status_usdt': True
        })

# ব্যাকগ্রাউন্ডে ইনিশিয়ালাইজেশন কল করা
asyncio.ensure_future(create_indexes())
asyncio.ensure_future(setup_default_settings())

# ================= ⚡ [Ultra-Fast In-Memory Cache] =================
_settings_cache = {}
_cache_time = 0
CACHE_TTL = 30  # ৩০ সেকেন্ড পর পর ক্যাশ রিলিজ হবে

async def _get_cached_settings():
    global _settings_cache, _cache_time
    now = time.time()
    if not _settings_cache or (now - _cache_time > CACHE_TTL):
        data = await settings_col.find_one({'_id': 'task_settings'}) or {}
        _settings_cache = data
        _cache_time = now
    return _settings_cache

# ================= Database Helper Functions =================

async def get_setting(key):
    settings = await _get_cached_settings()
    return settings.get(key)

async def update_setting(key, value):
    global _settings_cache
    await settings_col.update_one({'_id': 'task_settings'}, {'$set': {key: value}}, upsert=True)
    _settings_cache[key] = value

async def is_task_type_active(task_type):
    status = await get_setting(f'is_active_{task_type}')
    return True if status is None else status

async def toggle_task_type_status(task_type):
    current_status = await is_task_type_active(task_type)
    await update_setting(f'is_active_{task_type}', not current_status)
    return not current_status

async def get_balance(user_id):
    user = await users_col.find_one({'user_id': user_id}, {'balance': 1})
    return user.get('balance', 0.00) if user else 0.00

async def update_balance(user_id, amount):
    await users_col.update_one({'user_id': user_id}, {'$inc': {'balance': amount}}, upsert=True)

async def is_banned(user_id):
    user = await users_col.find_one({'user_id': user_id}, {'is_banned': 1})
    return user.get('is_banned', False) if user else False

async def set_banned(user_id, status):
    await users_col.update_one({'user_id': user_id}, {'$set': {'is_banned': status}}, upsert=True)
