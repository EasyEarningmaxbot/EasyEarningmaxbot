import datetime
import threading
from bson.objectid import ObjectId
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import config
from database import is_banned, get_balance, get_setting, users_col, withdrawals_col, tasks_col
from keyboards import main_menu, cancel_keyboard, withdraw_menu
from startHandler import check_membership

# -------------------------------------------------------------
# 🌐 Web3 / Auto Crypto Payout Function (USDT BEP-20)
# -------------------------------------------------------------
def execute_bep20_usdt_transfer(to_address, usd_amount):
    """
    web3 লাইব্রেরি ব্যবহার করে BSC নেটওয়ার্কে সরাসরি USDT BEP-20 সেন্ড করে।
    """
    try:
        from web3 import Web3
        
        w3 = Web3(Web3.HTTPProvider(config.BSC_RPC_URL))
        if not w3.is_connected():
            return {'success': False, 'error': 'BSC Node-এ কানেক্ট হওয়া যায়নি!'}

        account = w3.eth.account.from_key(config.METAMASK_PRIVATE_KEY)
        sender_address = account.address

        # USDT Minimal ABI for Transfer
        usdt_abi = [
            {
                "constant": False,
                "inputs": [
                    {"name": "_to", "type": "address"},
                    {"name": "_value", "type": "uint256"}
                ],
                "name": "transfer",
                "outputs": [{"name": "", "type": "bool"}],
                "type": "function"
            }
        ]

        contract = w3.eth.contract(address=Web3.to_checksum_address(config.USDT_BEP20_CONTRACT), abi=usdt_abi)
        
        # 18 decimals on BSC USDT
        amount_in_wei = int(usd_amount * (10 ** 18))
        nonce = w3.eth.get_transaction_count(sender_address)

        tx = contract.functions.transfer(
            Web3.to_checksum_address(to_address),
            amount_in_wei
        ).build_transaction({
            'chainId': 56, # BSC Mainnet
            'gas': 100000,
            'gasPrice': w3.eth.gas_price,
            'nonce': nonce,
        })

        signed_tx = w3.eth.account.sign_transaction(tx, private_key=config.METAMASK_PRIVATE_KEY)
        tx_hash_bytes = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        tx_hash = w3.to_hex(tx_hash_bytes)

        return {
            'success': True,
            'txHash': tx_hash,
            'txLink': f"https://bscscan.com/tx/{tx_hash}"
        }

    except Exception as e:
        return {'success': False, 'error': str(e)}


def register(bot):
    # 🛠️ 'উত্তোলনের অনুরোধ' বা '📤 উত্তোলন' মেসেজ হ্যান্ডলার
    @bot.message_handler(func=lambda message: message.text in ['উত্তোলনের অনুরোধ', '📤 উত্তোলন'])
    def handle_withdraw_request(message):
        if is_banned(message.from_user.id) or not check_membership(bot, message.from_user.id): return
        user_id = message.from_user.id
        balance = get_balance(user_id)
        
        min_recharge = get_setting('min_withdraw_recharge') or 10.00
        if balance < min_recharge:
            bot.send_message(
                message.chat.id, 
                f'<tg-emoji emoji-id="6302916351430235741">❌</tg-emoji> আপনার অ্যাকাউন্টে পর্যাপ্ত ব্যালেন্স নেই। উইথড্র করার জন্য সর্বনিম্ন ৳{min_recharge:.2f} ব্যালেন্স থাকতে হবে।',
                parse_mode="HTML"
            )
            return
            
        msg_text = (
            '<tg-emoji emoji-id="6221736233970700254">💳</tg-emoji> '
            '<b>আপনি কোন মাধ্যমে টাকা উত্তোলন করতে চান? একটি অপশন সিলেক্ট করুন</b> '
            '<tg-emoji emoji-id="4956720180337050608">⤵️</tg-emoji>'
        )
        msg = bot.send_message(message.chat.id, msg_text, parse_mode="HTML", reply_markup=withdraw_menu())
        bot.register_next_step_handler(msg, process_withdraw_method)

    def process_withdraw_method(message):
        if message.text in ['বাতিল', '❌ বাতিল']:
            bot.clear_step_handler_by_chat_id(message.chat.id)
            bot.send_message(message.chat.id, "উত্তোলন বাতিল করা হয়েছে।", reply_markup=main_menu(message.from_user.id))
            return
            
        selected_text = message.text
        
        if 'বিকাশ' in selected_text:
            method = 'Bkash'
            prompt_msg = (
                '<tg-emoji emoji-id="6221736233970700254">💳</tg-emoji> '
                '<tg-emoji emoji-id="5348469219761626211">💖</tg-emoji> '
                '<b>Bkash নির্বাচন করেছেন।</b>, আপনার বিকাশ পার্সোনাল নম্বরটি সাবমিট করুন:'
                '<tg-emoji emoji-id="6167906330813142191">⤵️</tg-emoji>'
            )
        elif 'নগদ' in selected_text:
            method = 'Nagad'
            prompt_msg = (
                '<tg-emoji emoji-id="6190336264940559752">💰</tg-emoji> '
                '<tg-emoji emoji-id="5352985330628730418">🟠</tg-emoji> '
                '<b>Nagad নির্বাচন করেছেন।</b>, আপনার Nagad পার্সোনাল নম্বরটি সাবমিট করুন:'
                '<tg-emoji emoji-id="6167906330813142191">⤵️</tg-emoji>'
            )
        elif 'মোবাইল রিচার্জ' in selected_text or 'রিচার্জ' in selected_text:
            method = 'Recharge'
            prompt_msg = (
                '<tg-emoji emoji-id="5337132498965010628">📱</tg-emoji> '
                'আপনার মোবাইল রিচার্জ নম্বরটি সাবমিট করুন:'
                '<tg-emoji emoji-id="6167906330813142191">⤵️</tg-emoji>'
            )
        elif 'USDT' in selected_text:
            method = 'USDT (BEP-20)'
            prompt_msg = (
                '<tg-emoji emoji-id="6206155797722830770">💎</tg-emoji><tg-emoji emoji-id="5228701849099473411">🟡</tg-emoji> '
                '<b>BEP20 (USDT) নির্বাচন করেছেন।</b>\n\n'
                'আপনার BEP20 Wallet Address (0x...) দিন<tg-emoji emoji-id="6206368810920841771">⤵️</tg-emoji>'
            )
        else:
            bot.send_message(message.chat.id, "❌ সঠিক মাধ্যম সিলেক্ট করেননি।", reply_markup=main_menu(message.from_user.id))
            return

        msg = bot.send_message(message.chat.id, prompt_msg, parse_mode="HTML", reply_markup=cancel_keyboard())
        bot.register_next_step_handler(msg, process_withdraw_number, method)

    def process_withdraw_number(message, method):
        if message.text in ['বাতিল', '❌ বাতিল']:
            bot.clear_step_handler_by_chat_id(message.chat.id)
            bot.send_message(message.chat.id, "উত্তোলন বাতিল করা হয়েছে।", reply_markup=main_menu(message.from_user.id))
            return
            
        number = message.text.strip()
        
        if method == 'Bkash':
            min_bkash = get_setting('min_withdraw_bkash') or 110.00
            prompt_amt = (
                f'<tg-emoji emoji-id="5348469219761626211">💖</tg-emoji> আপনার Bkash Number পাওয়া গেছে : {number}\n\n'
                f'<tg-emoji emoji-id="6221736233970700254">💳</tg-emoji> কত টাকা উত্তোলন করতে চান? (সর্বনিম্ন ৳{min_bkash:.2f}) নিচে এমাউন্টে লিখুন চার্জ ফ্রি ৫ টাকা '
                f'<tg-emoji emoji-id="6167906330813142191">⤵️</tg-emoji>'
            )
        elif method == 'Nagad':
            min_nagad = get_setting('min_withdraw_nagad') or 10.00
            prompt_amt = (
                f'<tg-emoji emoji-id="5352985330628730418">🟠</tg-emoji> আপনার Nagad Number পাওয়া গেছে : {number}\n\n'
                f'<tg-emoji emoji-id="6221736233970700254">💳</tg-emoji> কত টাকা উত্তোলন করতে চান? (সর্বনিম্ন ৳{min_nagad:.2f}) নিচে এমাউন্টে লিখুন চার্জ ফ্রি ৫ টাকা '
                f'<tg-emoji emoji-id="6167906330813142191">⤵️</tg-emoji>'
            )
        elif method == 'Recharge':
            prompt_amt = (
                '<tg-emoji emoji-id="6190336264940559752">💰</tg-emoji> '
                'কত টাকা রিচার্জ করতে চান সেই পরিমাণটি লিখুন'
                '<tg-emoji emoji-id="6167906330813142191">⤵️</tg-emoji>'
            )
        elif method == 'USDT (BEP-20)':
            min_usdt = get_setting('min_withdraw_usdt') or 25.00
            prompt_amt = (
                f'<tg-emoji emoji-id="6253780692908378898">🪙</tg-emoji> BEP20 Wallet Address (0x...): <code>{number}</code>\n\n'
                f'কত টাকা উত্তোলন করতে চান? (সর্বনিম্ন ৳{min_usdt:.2f})<tg-emoji emoji-id="4956720180337050608">⤵️</tg-emoji>'
            )
        else:
            fee_info = "(⚠️ মোবাইল রিচার্জ ব্যতীত অন্যান্য উত্তোলনে ৫ টাকা ফি প্রযোজ্য)"
            prompt_amt = f"💰 কত টাকা উইথড্র করতে চান সেই পরিমাণটি লিখুন:\n{fee_info}"

        msg = bot.send_message(message.chat.id, prompt_amt, parse_mode="HTML", reply_markup=cancel_keyboard())
        bot.register_next_step_handler(msg, process_withdraw_amount, method, number)

    def process_withdraw_amount(message, method, number):
        if message.text in ['বাতিল', '❌ বাতিল']:
            bot.clear_step_handler_by_chat_id(message.chat.id)
            bot.send_message(message.chat.id, "উত্তোলন বাতিল করা হয়েছে।", reply_markup=main_menu(message.from_user.id))
            return
            
        try:
            amount = float(message.text)
            user_id = message.from_user.id
            balance = get_balance(user_id)
            
            if method == 'Bkash':
                min_w = get_setting('min_withdraw_bkash') or 110.00
                fee = 5.00
            elif method == 'Nagad':
                min_w = get_setting('min_withdraw_nagad') or 10.00
                fee = 5.00
            elif method == 'Recharge':
                min_w = get_setting('min_withdraw_recharge') or 10.00
                fee = 5.00
            elif method == 'USDT (BEP-20)':
                min_w = get_setting('min_withdraw_usdt') or 25.00
                fee = 0.00
            else:
                min_w = 50.00
                fee = 5.00
                
            total_deduction = amount + fee
            
            if amount < min_w or total_deduction > balance:
                bot.send_message(
                    message.chat.id, 
                    f'<tg-emoji emoji-id="6302916351430235741">❌</tg-emoji> আপনার অ্যাকাউন্টে পর্যাপ্ত ব্যালেন্স নেই। উইথড্র করার জন্য সর্বনিম্ন ৳{min_w:.2f} ব্যালেন্স থাকতে হবে।', 
                    parse_mode="HTML",
                    reply_markup=main_menu(user_id)
                )
                return

            # ================= ⚡️ USDT BEP-20 AUTO PAYOUT LOGIC =================
            if method == 'USDT (BEP-20)':
                usd_rate = get_setting('usd_rate') or config.USD_EXCHANGE_RATE
                usd_received = round(amount / usd_rate, 4)

                # ব্যালেন্স সাময়িকভাবে হোল্ড করা
                users_col.update_one({'user_id': user_id}, {'$inc': {'balance': -amount, 'pending_withdraw': amount}})
                
                processing_msg = (
                    f'<tg-emoji emoji-id="5782742034599121928">⏳</tg-emoji> <b>আপনার উত্তোলন প্রসেস হচ্ছে...</b>\n\n'
                    f'<tg-emoji emoji-id="6253780692908378898">📌</tg-emoji> <b>মাধ্যম:</b> <tg-emoji emoji-id="5228701849099473411">🟡</tg-emoji> BEP20 (USDT)\n'
                    f'<tg-emoji emoji-id="5409048419211682843">💵</tg-emoji> <b>পরিমাণ:</b> ৳{amount:.2f} BDT\n'
                    f'<tg-emoji emoji-id="5807908953815781702">📥</tg-emoji> <b>পাবেন:</b> {usd_received:.2f} USDT\n'
                    f'<tg-emoji emoji-id="5231200819986047254">📊</tg-emoji> <b>Rate:</b> ৳{usd_rate:.0f} = $1\n\n'
                    f'<tg-emoji emoji-id="5199785165735367039">⚡️</tg-emoji> Auto Pay দিয়ে পেমেন্ট হবে, কয়েক সেকেন্ডের মধ্যে কনফার্মেশন পাবেন<tg-emoji emoji-id="6256016519738691544">✨</tg-emoji>'
                )
                bot.send_message(message.chat.id, processing_msg, parse_mode="HTML", reply_markup=main_menu(user_id))

                def _background_usdt_payout():
                    res = execute_bep20_usdt_transfer(number, usd_received)

                    if res.get('success'):
                        tx_hash = res.get('txHash', '')
                        tx_link = res.get('txLink', '')

                        # ডাটাবেজে উইথড্র কনফার্ম সেভ
                        wd_doc = {
                            'user_id': user_id, 
                            'first_name': message.from_user.first_name, 
                            'username': message.from_user.username or "None",
                            'method': '🔷 BEP20 (USDT)', 
                            'number': number, 
                            'amount': amount, 
                            'usd_amount': usd_received,
                            'tx_hash': tx_hash,
                            'status': 'Approved', 
                            'date': datetime.datetime.now()
                        }
                        withdrawals_col.insert_one(wd_doc)
                        users_col.update_one({'user_id': user_id}, {'$inc': {'pending_withdraw': -amount}})

                        # ১. ইউজারকে সাফল্য বার্তা পাঠানো
                        user_success_msg = (
                            f'<tg-emoji emoji-id="6125457176161948466">🎉</tg-emoji> <b>Payment Successful!</b>\n'
                            f'┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n'
                            f'<tg-emoji emoji-id="6221736233970700254">💳</tg-emoji> <b>পরিমাণ  :</b> ৳{amount:.2f} BDT\n'
                            f'<tg-emoji emoji-id="5409048419211682843">💵</tg-emoji> <b>পেয়েছেন :</b> {usd_received} USDT\n'
                            f'<tg-emoji emoji-id="6253780692908378898">🌐</tg-emoji> <b>Network :</b> <tg-emoji emoji-id="5228701849099473411">🟡</tg-emoji> BEP20 (USDT)\n'
                            f'<tg-emoji emoji-id="4958689671950369798">🔗</tg-emoji> <b>TxHash  :</b> <a href="{tx_link}">{tx_hash}</a>\n'
                            f'┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n'
                            f'<tg-emoji emoji-id="6253353798928959936">✅</tg-emoji> <b>আপনার Payment সম্পন্ন হয়েছে! ধন্যবাদ</b> <tg-emoji emoji-id="4956649845952611245">❤️</tg-emoji>'
                        )
                        try: bot.send_message(user_id, user_success_msg, parse_mode="HTML", disable_web_page_preview=True)
                        except: pass

                        # ২. মেম্বারের ইনকাম ও টাস্ক হিসাব আনা
                        u_data = users_col.find_one({'user_id': user_id}) or {}
                        completed_tasks = u_data.get('completed_tasks', 0)
                        ref_income = u_data.get('ref_income', 0.0)
                        task_income = u_data.get('total_income', 0.0) - ref_income
                        total_income = u_data.get('total_income', 0.0)

                        # ৩. পেমেন্ট প্রুফ চ্যানেলে কাস্টম ইমোজি সহ অটো নোটিশ পাঠানো
                        channel_proof_msg = (
                            '<tg-emoji emoji-id="6253353798928959936">✅</tg-emoji> <b>Withdrawal Approved!</b>\n'
                            '━━━━━━━━━━━━━━━━━━━━━━\n'
                            f'<tg-emoji emoji-id="5352861489541714456">👤</tg-emoji> <b>User:</b> {message.from_user.first_name} (<code>{user_id}</code>)\n'
                            f'<tg-emoji emoji-id="5332687864943626828">💳</tg-emoji> <b>Method:</b> <tg-emoji emoji-id="5228701849099473411">🟡</tg-emoji> BEP20 (USDT)\n'
                            f'<tg-emoji emoji-id="6206245785877616415">📱</tg-emoji> <b>Account:</b> <code>{number}</code>\n'
                            f'<tg-emoji emoji-id="6190336264940559752">💰</tg-emoji> <b>Amount:</b> ৳{amount:.2f}\n'
                            f'<tg-emoji emoji-id="6206155797722830770">💵</tg-emoji> <b>User Received:</b> {usd_received} USDT\n'
                            f'<tg-emoji emoji-id="4958689671950369798">🔗</tg-emoji> <b>TxHash:</b> <a href="{tx_link}">{tx_hash}</a>\n'
                            '━━━━━━━━━━━━━━━━━━━━━━\n'
                            f'📊 <b>Earning Breakdown (মোট {completed_tasks}টি Approved Task):</b>\n'
                            f'<tg-emoji emoji-id="5364310996179503764">📘</tg-emoji><tg-emoji emoji-id="5389064576333527180">📸</tg-emoji> <b>Facebook + Instagram Tasks:</b> {completed_tasks}টি — ৳{task_income:.2f}\n'
                            '━━━━━━━━━━━━━━━━━━━━━━\n'
                            f'<tg-emoji emoji-id="6190336264940559752">🧾</tg-emoji> <b>Task থেকে মোট:</b> ৳{task_income:.2f}\n'
                            f'<tg-emoji emoji-id="6206150489143252478">👥</tg-emoji> <b>Referral থেকে মোট:</b> ৳{ref_income:.2f}\n'
                            f'<tg-emoji emoji-id="6206465524994414050">💰</tg-emoji> <b>সর্বমোট আয় (Task + Referral):</b> ৳{total_income:.2f}\n'
                            '━━━━━━━━━━━━━━━━━━━━━━'
                        )
                        try:
                            bot.send_message(config.PAYMENT_PROOF_CHANNEL_ID, channel_proof_msg, parse_mode="HTML", disable_web_page_preview=True)
                        except Exception as err:
                            print(f"Channel Proof Error: {err}")

                    else:
                        # পেমেন্ট ফেইল করলে ম্যানুয়াল রিভিউতে রাখা
                        err_msg = res.get('error', 'Unknown Error')
                        users_col.update_one({'user_id': user_id}, {'$inc': {'balance': total_deduction, 'pending_withdraw': -amount}})
                        bot.send_message(user_id, f"⚠️ <b>অটো উইথড্র সফল হয়নি ({err_msg})! আপনার টাকা ব্যালেন্সে ফেরত দেওয়া হয়েছে। এডমিন ম্যানুয়ালি ব্যবস্থা নেবে।</b>", parse_mode="HTML")

                threading.Thread(target=_background_usdt_payout, daemon=True).start()
                return

            # ================= 📱 বিকাশ, নগদ ও রিচার্জ ম্যানুয়াল উইথড্র =================
            users_col.update_one({'user_id': user_id}, {'$inc': {'balance': -total_deduction, 'pending_withdraw': amount}})
            
            wd_doc = {
                'user_id': user_id, 
                'first_name': message.from_user.first_name, 
                'username': message.from_user.username or "None",
                'method': method, 
                'number': number, 
                'amount': amount, 
                'fee': fee,
                'status': 'Pending', 
                'date': datetime.datetime.now()
            }
            inserted_id = withdrawals_col.insert_one(wd_doc).inserted_id
            
            if method == 'Recharge':
                success_msg = (
                    f'<tg-emoji emoji-id="5337132498965010628">📱</tg-emoji> আপনার ৳{amount:.2f} রিচার্জ রিকোয়েস্ট সফলভাবে জমা হয়েছে '
                    f'(এবং ৳{fee:.2f} ফি কাটা হয়েছে)। এটি পেন্ডিং বক্সে যুক্ত হয়েছে'
                    f'<tg-emoji emoji-id="5136508653808911452">✅</tg-emoji>'
                )
            elif method == 'Nagad':
                success_msg = (
                    f'<tg-emoji emoji-id="5352985330628730418">🟠</tg-emoji> আপনার ৳{amount:.2f} উইথড্র রিকোয়েস্ট সফলভাবে জমা হয়েছে '
                    f'(এবং ৳{fee:.2f} ফি কাটা হয়েছে)। এটি পেন্ডিং বক্সে যুক্ত হয়েছে।'
                    f'<tg-emoji emoji-id="5136508653808911452">✅</tg-emoji>'
                )
            elif method == 'Bkash':
                success_msg = (
                    f'<tg-emoji emoji-id="5348469219761626211">💖</tg-emoji> আপনার ৳{amount:.2f} উইথড্র রিকোয়েস্ট সফলভাবে জমা হয়েছে '
                    f'(এবং ৳{fee:.2f} ফি কাটা হয়েছে)। এটি পেন্ডিং বক্সে যুক্ত হয়েছে।'
                    f'<tg-emoji emoji-id="5136508653808911452">✅</tg-emoji>'
                )
            else:
                success_msg = f"✅ আপনার ৳{amount:.2f} উইথড্র রিকোয়েস্ট সফলভাবে জমা হয়েছে।"

            bot.send_message(message.chat.id, success_msg, parse_mode="HTML", reply_markup=main_menu(user_id))
            
            # উইথড্র গ্রুপ ফরওয়ার্ড মেসেজ
            if method == 'Recharge':
                group_msg_text = (
                    f'<tg-emoji emoji-id="6307777408300753473">🆔</tg-emoji> <b>User ID:</b> <code>{user_id}</code>\n'
                    f'<tg-emoji emoji-id="6206465524994414050">👤</tg-emoji> <b>Name:</b> {message.from_user.first_name}\n'
                    f'<tg-emoji emoji-id="5337132498965010628">📥</tg-emoji> <b>মাধ্যম:</b> রিচার্জ\n'
                    f'<tg-emoji emoji-id="5337132498965010628">📱</tg-emoji> <b>অ্যাকাউন্ট/নাম্বার:</b> <code>{number}</code>\n'
                    f'<tg-emoji emoji-id="6190336264940559752">💰</tg-emoji> <b>পরিমাণ:</b> {amount:.2f}৳'
                )
            elif method == 'Nagad':
                group_msg_text = (
                    f'<tg-emoji emoji-id="6307777408300753473">🆔</tg-emoji> <b>User ID:</b> <code>{user_id}</code>\n'
                    f'<tg-emoji emoji-id="6206465524994414050">👤</tg-emoji> <b>Name:</b> {message.from_user.first_name}\n'
                    f'<tg-emoji emoji-id="5352985330628730418">📥</tg-emoji> <b>মাধ্যম:</b> {method}\n'
                    f'<tg-emoji emoji-id="5352985330628730418">📱</tg-emoji> <b>অ্যাকাউন্ট/নাম্বার:</b> <code>{number}</code>\n'
                    f'<tg-emoji emoji-id="6190336264940559752">💰</tg-emoji> <b>পরিমাণ:</b> ৳{amount:.2f}\n'
                    f'<tg-emoji emoji-id="6203750195130274981">⚡️</tg-emoji> <b>ফ্রি কাটা হইছে:</b> {fee:.2f} BDT'
                )
            else: # Bkash / Others
                group_msg_text = (
                    f'<tg-emoji emoji-id="5352861489541714456">🆔</tg-emoji> <b>User ID:</b> <code>{user_id}</code>\n'
                    f'<tg-emoji emoji-id="6206465524994414050">👤</tg-emoji> <b>Name:</b> {message.from_user.first_name}\n'
                    f'<tg-emoji emoji-id="5348469219761626211">📥</tg-emoji> <b>মাধ্যম:</b> {method}\n'
                    f'<tg-emoji emoji-id="5348469219761626211">📱</tg-emoji> <b>অ্যাকাউন্ট/নাম্বার:</b> <code>{number}</code>\n'
                    f'<tg-emoji emoji-id="6190336264940559752">💰</tg-emoji> <b>পরিমাণ:</b> ৳{amount:.2f}\n'
                    f'<tg-emoji emoji-id="6203750195130274981">⚡️</tg-emoji> <b>ফ্রি কাটা হইছে:</b> {fee:.2f} BDT'
                )
            
            inline_markup = InlineKeyboardMarkup()
            inline_markup.add(
                InlineKeyboardButton("এপ্রুভ", callback_data=f"gr_wd_approve_{inserted_id}"),
                InlineKeyboardButton("রিজেক্ট", callback_data=f"gr_wd_reject_{inserted_id}")
            )
            
            try:
                bot.send_message(config.WITHDRAW_GROUP_ID, group_msg_text, parse_mode="HTML", reply_markup=inline_markup)
            except Exception as e:
                print(f"Group Delivery Error: {e}")
                
        except Exception as e:
            bot.send_message(message.chat.id, "❌ সঠিক সংখ্যা লিখুন।", reply_markup=main_menu(message.from_user.id))

    @bot.callback_query_handler(func=lambda call: call.data.startswith('gr_wd_'))
    def handle_group_withdraw_buttons(call):
        parts = call.data.split('_')
        action = parts[2]
        wd_id = ObjectId(parts[3])
        
        w = withdrawals_col.find_one({'_id': wd_id})
        if not w or w['status'] != 'Pending':
            bot.answer_callback_query(call.id, "⚠️ এই রিকোয়েস্টটি ইতিমধ্যে প্রসেস করা হয়েছে!", show_alert=True)
            return

        user_id = w['user_id']
        amount = w['amount']
        method = w.get('method', '')
        fee = w.get('fee', 5.00)
        
        if action == 'approve':
            users_col.update_one({'user_id': user_id}, {'$inc': {'pending_withdraw': -amount}})
            withdrawals_col.update_one({'_id': wd_id}, {'$set': {'status': 'Approved'}})
            
            bot.edit_message_text(f"{call.message.text}\n\n✅ <b>APPROVED BY ADMIN</b>", call.message.chat.id, call.message.message_id, parse_mode="HTML")
            
            if method == 'Recharge':
                approve_user_msg = (
                    '<tg-emoji emoji-id="6125457176161948466">🎉</tg-emoji> '
                    'আপনার রিচার্জ সফলভাবে হয়েছে এবং আপনার ওয়ালেটে টাকা চলে গেছে মনোযোগ দিয়ে কাজ করুন'
                    '<tg-emoji emoji-id="4956720180337050608">❤️</tg-emoji>'
                )
            else:
                approve_user_msg = (
                    '<tg-emoji emoji-id="6125457176161948466">🎉</tg-emoji> '
                    'আপনার উত্তোলন সফলভাবে হয়েছে এবং আপনার ওয়ালেটে টাকা চলে গেছে মনোযোগ দিয়ে কাজ করুন'
                    '<tg-emoji emoji-id="4956720180337050608">❤️</tg-emoji>'
                )

            try:
                bot.send_message(user_id, approve_user_msg, parse_mode="HTML")
            except: pass
            bot.answer_callback_query(call.id, "✅ উইথড্র সফলভাবে এপ্রুভড!", show_alert=True)

            # ম্যানুয়াল পেমেন্ট চ্যানেল প্রুফ পোস্ট
            u_data = users_col.find_one({'user_id': user_id}) or {}
            completed_tasks = u_data.get('completed_tasks', 0)
            ref_income = u_data.get('ref_income', 0.0)
            task_income = u_data.get('total_income', 0.0) - ref_income
            total_income = u_data.get('total_income', 0.0)

            channel_proof_msg = (
                '<tg-emoji emoji-id="6253353798928959936">✅</tg-emoji> <b>Withdrawal Approved!</b>\n'
                '━━━━━━━━━━━━━━━━━━━━━━\n'
                f'<tg-emoji emoji-id="5352861489541714456">👤</tg-emoji> <b>User:</b> {w.get("first_name", "User")} (<code>{user_id}</code>)\n'
                f'<tg-emoji emoji-id="5332687864943626828">💳</tg-emoji> <b>Method:</b> {method}\n'
                f'<tg-emoji emoji-id="6206245785877616415">📱</tg-emoji> <b>Account:</b> <code>{w.get("number", "")}</code>\n'
                f'<tg-emoji emoji-id="6190336264940559752">💰</tg-emoji> <b>Amount:</b> ৳{amount:.2f}\n'
                '━━━━━━━━━━━━━━━━━━━━━━\n'
                f'📊 <b>Earning Breakdown (মোট {completed_tasks}টি Approved Task):</b>\n'
                f'<tg-emoji emoji-id="5364310996179503764">📘</tg-emoji><tg-emoji emoji-id="5389064576333527180">📸</tg-emoji> <b>Facebook + Instagram Tasks:</b> {completed_tasks}টি — ৳{task_income:.2f}\n'
                '━━━━━━━━━━━━━━━━━━━━━━\n'
                f'<tg-emoji emoji-id="6190336264940559752">🧾</tg-emoji> <b>Task থেকে মোট:</b> ৳{task_income:.2f}\n'
                f'<tg-emoji emoji-id="6206150489143252478">👥</tg-emoji> <b>Referral থেকে মোট:</b> ৳{ref_income:.2f}\n'
                f'<tg-emoji emoji-id="6206465524994414050">💰</tg-emoji> <b>সর্বমোট আয় (Task + Referral):</b> ৳{total_income:.2f}\n'
                '━━━━━━━━━━━━━━━━━━━━━━'
            )
            try:
                bot.send_message(config.PAYMENT_PROOF_CHANNEL_ID, channel_proof_msg, parse_mode="HTML")
            except Exception as e:
                print(f"Proof Post Error: {e}")

        elif action == 'reject':
            total_refund = amount + fee
            users_col.update_one({'user_id': user_id}, {'$inc': {'pending_withdraw': -amount, 'balance': total_refund}})
            withdrawals_col.update_one({'_id': wd_id}, {'$set': {'status': 'Rejected'}})
            
            bot.edit_message_text(f"{call.message.text}\n\n❌ <b>REJECTED BY ADMIN</b>", call.message.chat.id, call.message.message_id, parse_mode="HTML")
            
            try:
                bot.send_message(user_id, "আপনার উত্তোলনটি রিজেক্ট করা হয়েছে মনোযোগ দিয়ে কাজ করুন")
            except: pass
            bot.answer_callback_query(call.id, "❌ উইথড্র রিজেক্ট করা হয়েছে!", show_alert=True)
