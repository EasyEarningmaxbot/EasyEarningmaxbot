# ================= TERMUX DNS FIX =================
import dns.resolver

try:
    dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
    dns.resolver.default_resolver.nameservers = ['8.8.8.8', '1.1.1.1']
except Exception:
    pass

import urllib.parse

# ================= BOT TOKEN & IDS =================
BOT_TOKEN = '8939356064:AAEbROtJwBeBTJdIRcnOgNfvMMnq_LFgEjU'

ADMIN_IDS = [6084022488]
WITHDRAW_GROUP_ID = -1004400567428   # বিকাশ, নগদ ও রিচার্জের জন্য ম্যানুয়াল গ্রুপ
TASK_LOG_GROUP_ID = -1003968613056     

# ================= CHANNELS & PROOF =================
OFFICIAL_CHANNEL_ID = '@NexUpChannel'
OFFICIAL_CHANNEL_LINK = "https://t.me/NexUpChannel" 

PAYMENT_PROOF_CHANNEL_ID = -1004424968918
PAYMENT_PROOF_CHANNEL_LINK = "https://t.me/paymentproofchannel8"

# বটে ঢুকতে যে ২টি চ্যানেলে জয়েন থাকা বাধ্যতামূলক
REQUIRED_CHANNELS = [
    {'id': '@NexUpChannel', 'link': OFFICIAL_CHANNEL_LINK, 'name': 'অফিশিয়াল চ্যানেল'},
    {'id': PAYMENT_PROOF_CHANNEL_ID, 'link': PAYMENT_PROOF_CHANNEL_LINK, 'name': 'পেমেন্ট প্রুফ চ্যানেল'}
]

SUPPORT_CHANNEL_LINK = "https://t.me/NexUpChannel" 

# ================= MONGODB URI =================
MONGO_URI = "mongodb+srv://demu1001_db_user:Yasin0179649@cluster0.k6vlkca.mongodb.net/?retryWrites=true&w=majority"

# ================= USDT BEP-20 AUTO PAYOUT CONFIG =================
BSC_RPC_URL = "https://bsc-dataseed.binance.org/"
METAMASK_PRIVATE_KEY = "30bf9ceeefd2eab7581637a820a6c04bde3f5f90d86258fc69668a7b7f5f2bbf"
USDT_BEP20_CONTRACT = "0x55d398326f99059fF775485246999027B3197955"  # BSC USDT Contract Address
USD_EXCHANGE_RATE = 120.0  # ১ ডলার (USDT) = ১২০ টাকা (BDT)
