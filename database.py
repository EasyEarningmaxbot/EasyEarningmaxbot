from pymongo import MongoClient, ASCENDING
import config
import time

client = MongoClient(config.MONGO_URI)
db = client['easyincomedb']

users_col = db['users']
tasks_col = db['tasks']
withdrawals_col = db['withdrawals']
settings_col = db['settings']

# 🚀 [Performance Optimization] MongoDB Indexing
# এর ফলে লাখ লাখ ডাটা থাকলেও ১ মিলিসেকেন্ডে রেজাল্ট চলে আসবে
users_col.create_index([("user_id", ASCENDING)], unique=True)
users_col.create_index([("completed_tasks", -1)])
tasks_col.create_index([("2fa_key", ASCENDING)])
tasks_col.create_index([("fb_uid", ASCENDING)])

print("MongoDB successfully connected and Indexes Created!")

# Default settings setup
if not settings_col.find_one({'_id': 'task_settings'}):
    settings_col.insert_one({
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
        'leaderboard_prizes': '100,50,30,20,10'
    })

# ⚡ [In-Memory Cache] সেটিংস বারবার ডাটাবেস থেকে রিড না করে মেমোরি থেকে দ্রুত লোড করবে
_settings_cache = {}
_cache_time = 0
CACHE_TTL = 30  # ৩০ সেকেন্ড পর পর ক্যাশ রিলিজ হবে

def _get_cached_settings():
    global _settings_cache, _cache_time
    now = time.time()
    if not _settings_cache or (now - _cache_time > CACHE_TTL):
        data = settings_col.find_one({'_id': 'task_settings'}) or {}
        _settings_cache = data
        _cache_time = now
    return _settings_cache

def get_setting(key):
    settings = _get_cached_settings()
    return settings.get(key)

def update_setting(key, value):
    global _settings_cache
    settings_col.update_one({'_id': 'task_settings'}, {'$set': {key: value}})
    _settings_cache[key] = value

# Specific task type status check
def is_task_type_active(task_type):
    status = get_setting(f'is_active_{task_type}')
    return True if status is None else status

def toggle_task_type_status(task_type):
    current_status = is_task_type_active(task_type)
    update_setting(f'is_active_{task_type}', not current_status)
    return not current_status

def get_balance(user_id):
    user = users_col.find_one({'user_id': user_id}, {'balance': 1})
    return user.get('balance', 0.00) if user else 0.00

def update_balance(user_id, amount):
    users_col.update_one({'user_id': user_id}, {'$inc': {'balance': amount}}, upsert=True)

def is_banned(user_id):
    user = users_col.find_one({'user_id': user_id}, {'is_banned': 1})
    return user.get('is_banned', False) if user else False

def set_banned(user_id, status):
    users_col.update_one({'user_id': user_id}, {'$set': {'is_banned': status}}, upsert=True)
