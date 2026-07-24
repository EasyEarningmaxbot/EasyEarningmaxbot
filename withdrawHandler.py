import datetime
import asyncio
import logging
from bson.objectid import ObjectId
from aiogram import Router, types, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

import config
from database import is_banned, get_balance, get_setting, users_col, withdrawals_col
from keyboards import main_menu, cancel_keyboard, withdraw_menu
from startHandler import check_membership

router = Router()

# -------------------------------------------------------------
# 🛠️ FSM States (উইথড্র ফ্লো এর জন্য)
# -------------------------------------------------------------
class WithdrawStates(StatesGroup):
    waiting_method = State()
    waiting_number = State()
    waiting_amount = State()

# -------------------------------------------------------------
# 🌐 Web3 / Auto Crypto Payout Function (USDT BEP-20 - Async Wrapper)
# -------------------------------------------------------------
def _sync_bep20_transfer(to_address, usd_amount):
    """
    ব্লকচেইন ট্রানজেকশন ব্যাকগ্রাউন্ডে চালানোর জন্য সিঙ্ক ফাংশন।
    """
    try:
        from web3 import Web3
        
        w3 = Web3(Web3.HTTPProvider(config.BSC_RPC_URL))
        if not w3.is_connected():
            return {'success': False, 'error': 'BSC Node-এ কানেক্ট হওয়া যায়নি!'}

        account = w3.eth.account.from_key(config.METAMASK_PRIVATE_KEY)
        sender_address = account.address

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
        
        amount_in_wei = int(usd_amount * (10 ** 18))
        nonce = w3.eth.get_transaction_count(sender_address)

        tx = contract.functions.transfer(
            Web3.to_checksum_address(to_address),
            amount_in_wei
        ).build_transaction({
            'chainId': 56,
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

async def execute_bep20_usdt_transfer(to_address, usd_amount):
    """
    অ্যাসিঙ্ক্রোনাসভাবে ব্লকচেইন ট্রানজেকশন এক্সিকিউট করে যাতে বটের থ্রেড না আটকে।
    """
    return await asyncio.to_thread(_sync_bep20_transfer, to_address, usd_amount)

# -------------------------------------------------------------
# 💳 'উত্তোলনের অনুরোধ' / '📤 উত্তোলন' বাটন হ্যান্ডলার
# -------------------------------------------------------------
@router.message(F.text.in_(['উত্তোলনের অনুরোধ', '📤 উত্তোলন']))
async def handle_withdraw_request(message: types.Message, bot: Bot, state: FSMContext):
    user_id = message.from_user.id
    if state: await state.clear()

    if await is_banned(user_id) or not await check_membership(bot, user_id):
        return

    balance = await get_balance(user_id)
    min_recharge = await get_setting('min_withdraw_recharge') or 10.00
    
    if balance < min_recharge:
        await message.answer(
            f'<tg-emoji emoji-id="6302916351430235741">❌</tg-emoji> আপনার অ্যাকাউন্টে পর্যাপ্ত ব্যালেন্স নেই। উইথড্র করার জন্য সর্বনিম্ন ৳{min_recharge:.2f} ব্যালেন্স থাকতে হবে।'
        )
        return
        
    msg_text = (
        '<tg-emoji emoji-id="6221736233970700254">💳</tg-emoji> '
        '<b>আপনি কোন মাধ্যমে টাকা উত্তোলন করতে চান? একটি অপশন সিলেক্ট করুন</b> '
        '<tg-emoji emoji-id="4956720180337050608">⤵️</tg-emoji>'
    )
    markup = await withdraw_menu() if callable(withdraw_menu) else withdraw_menu
    await message.answer(msg_text, reply_markup=markup)
    await state.set_state(WithdrawStates.waiting_method)

# -------------------------------------------------------------
# 🔄 মেথড সিলেক্ট স্টেপ
# -------------------------------------------------------------
@router.message(WithdrawStates.waiting_method)
async def process_withdraw_method(message: types.Message, state: FSMContext):
    selected_text = message.text

    if selected_text in ['বাতিল', '❌ বাতিল']:
        await state.clear()
        markup = await main_menu(message.from_user.id) if callable(main_menu) else main_menu
        await message.answer("উত্তোলন বাতিল করা হয়েছে।", reply_markup=markup)
        return
        
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
        markup = await main_menu(message.from_user.id) if callable(main_menu) else main_menu
        await message.answer("❌ সঠিক মাধ্যম সিলেক্ট করেননি।", reply_markup=markup)
        await state.clear()
        return

    await state.update_data(method=method)
    markup = await cancel_keyboard() if callable(cancel_keyboard) else cancel_keyboard
    await message.answer(prompt_msg, reply_markup=markup)
    await state.set_state(WithdrawStates.waiting_number)

# -------------------------------------------------------------
# 📱 নম্বর / ওয়ালেট অ্যাড্রেস ইনপুট স্টেপ
# -------------------------------------------------------------
@router.message(WithdrawStates.waiting_number)
async def process_withdraw_number(message: types.Message, state: FSMContext):
    if message.text in ['বাতিল', '❌ বাতিল']:
        await state.clear()
        markup = await main_menu(message.from_user.id) if callable(main_menu) else main_menu
        await message.answer("উত্তোলন বাতিল করা হয়েছে।", reply_markup=markup)
        return
        
    number = message.text.strip()
    data = await state.get_data()
    method = data.get('method')
    await state.update_data(number=number)

    if method == 'Bkash':
        min_bkash = await get_setting('min_withdraw_bkash') or 110.00
        prompt_amt = (
            f'<tg-emoji emoji-id="5348469219761626211">💖</tg-emoji> আপনার Bkash Number পাওয়া গেছে : {number}\n\n'
            f'<tg-emoji emoji-id="6221736233970700254">💳</tg-emoji> কত টাকা উত্তোলন করতে চান? (সর্বনিম্ন ৳{min_bkash:.2f}) নিচে এমাউন্টে লিখুন চার্জ ফ্রি ৫ টাকা '
            f'<tg-emoji emoji-id="6167906330813142191">⤵️</tg-emoji>'
        )
    elif method == 'Nagad':
        min_nagad = await get_setting('min_withdraw_nagad') or 10.00
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
        min_usdt = await get_setting('min_withdraw_usdt') or 25.00
        prompt_amt = (
            f'<tg-emoji emoji-id="6253780692908378898">🪙</tg-emoji> BEP20 Wallet Address (0x...): <code>{number}</code>\n\n'
            f'কত টাকা উত্তোলন করতে চান? (সর্বনিম্ন ৳{min_usdt:.2f})<tg-emoji emoji-id="4956720180337050608">⤵️</tg-emoji>'
        )
    else:
        fee_info = "(⚠️ মোবাইল রিচার্জ ব্যতীত অন্যান্য উত্তোলনে ৫ টাকা ফি প্রযোজ্য)"
        prompt_amt = f"💰 কত টাকা উইথড্র করতে চান সেই পরিমাণটি লিখুন:\n{fee_info}"

    markup = await cancel_keyboard() if callable(cancel_keyboard) else cancel_keyboard
    await message.answer(prompt_amt, reply_markup=markup)
    await state.set_state(WithdrawStates.waiting_amount)

# -------------------------------------------------------------
# 💵 পরিমাণ ইনপুট ও প্রসেসিং স্টেপ
# -------------------------------------------------------------
@router.message(WithdrawStates.waiting_amount)
async def process_withdraw_amount(message: types.Message, state: FSMContext, bot: Bot):
    if message.text in ['বাতিল', '❌ বাতিল']:
        await state.clear()
        markup = await main_menu(message.from_user.id) if callable(main_menu) else main_menu
        await message.answer("উত্তোলন বাতিল করা হয়েছে।", reply_markup=markup)
        return
        
    try:
        amount = float(message.text)
        user_id = message.from_user.id
        data = await state.get_data()
        method = data.get('method')
        number = data.get('number')
        await state.clear()

        balance = await get_balance(user_id)
        
        if method == 'Bkash':
            min_w = await get_setting('min_withdraw_bkash') or 110.00
            fee = 5.00
        elif method == 'Nagad':
            min_w = await get_setting('min_withdraw_nagad') or 10.00
            fee = 5.00
        elif method == 'Recharge':
            min_w = await get_setting('min_withdraw_recharge') or 10.00
            fee = 5.00
        elif method == 'USDT (BEP-20)':
            min_w = await get_setting('min_withdraw_usdt') or 25.00
            fee = 0.00
        else:
            min_w = 50.00
            fee = 5.00
            
        total_deduction = amount + fee
        
        if amount < min_w or total_deduction > balance:
            markup = await main_menu(user_id) if callable(main_menu) else main_menu
            await message.answer(
                f'<tg-emoji emoji-id="6302916351430235741">❌</tg-emoji> আপনার অ্যাকাউন্টে পর্যাপ্ত ব্যালেন্স নেই। উইথড্র করার জন্য সর্বনিম্ন ৳{min_w:.2f} ব্যালেন্স থাকতে হবে।', 
                reply_markup=markup
            )
            return

        # ================= ⚡️ USDT BEP-20 AUTO PAYOUT LOGIC =================
        if method == 'USDT (BEP-20)':
            usd_rate = await get_setting('usd_rate') or config.USD_EXCHANGE_RATE
            usd_received = round(amount / usd_rate, 4)

            # ব্যালেন্স সাময়িকভাবে হোল্ড করা (Async DB)
            await users_col.update_one({'user_id': user_id}, {'$inc': {'balance': -amount, 'pending_withdraw': amount}})
            
            processing_msg = (
                f'<tg-emoji emoji-id="5782742034599121928">⏳</tg-emoji> <b>আপনার উত্তোলন প্রসেস হচ্ছে...</b>\n\n'
                f'<tg-emoji emoji-id="6253780692908378898">📌</tg-emoji> <b>মাধ্যম:</b> <tg-emoji emoji-id="5228701849099473411">🟡</tg-emoji> BEP20 (USDT)\n'
                f'<tg-emoji emoji-id="5409048419211682843">💵</tg-emoji> <b>পরিমাণ:</b> ৳{amount:.2f} BDT\n'
                f'<tg-emoji emoji-id="5807908953815781702">📥</tg-emoji> <b>পাবেন:</b> {usd_received:.2f} USDT\n'
                f'<tg-emoji emoji-id="5231200819986047254">📊</tg-emoji> <b>Rate:</b> ৳{usd_rate:.0f} = $1\n\n'
                f'<tg-emoji emoji-id="5199785165735367039">⚡️</tg-emoji> Auto Pay দিয়ে পেমেন্ট হবে, কয়েক সেকেন্ডের মধ্যে কনফার্মেশন পাবেন<tg-emoji emoji-id="6256016519738691544">✨</tg-emoji>'
            )
            markup = await main_menu(user_id) if callable(main_menu) else main_menu
            await message.answer(processing_msg, reply_markup=markup)

            # ব্যাকগ্রাউন্ড টাস্ক সম্পূর্ণ অ্যাসিনক্রোনাসলি চালানো
            asyncio.create_task(_async_usdt_payout(bot, user_id, message.from_user.first_name, message.from_user.username, number, amount, usd_received))
            return

        # ================= 📱 বিকাশ, নগদ ও রিচার্জ ম্যানუალ উইথড্র =================
        await users_col.update_one({'user_id': user_id}, {'$inc': {'balance': -total_deduction, 'pending_withdraw': amount}})
        
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
        res = await withdrawals_col.insert_one(wd_doc)
        inserted_id = res.inserted_id
        
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

        markup = await main_menu(user_id) if callable(main_menu) else main_menu
        await message.answer(success_msg, reply_markup=markup)
        
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
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="এপ্রুভ", callback_data=f"gr_wd_approve_{inserted_id}"),
            InlineKeyboardButton(text="রিজেক্ট", callback_data=f"gr_wd_reject_{inserted_id}")
        )
        
        try:
            await bot.send_message(config.WITHDRAW_GROUP_ID, group_msg_text, reply_markup=builder.as_markup())
        except Exception as e:
            logging.error(f"Group Delivery Error: {e}")
            
    except Exception as e:
        markup = await main_menu(message.from_user.id) if callable(main_menu) else main_menu
        await message.answer("❌ সঠিক সংখ্যা লিখুন।", reply_markup=markup)

# -------------------------------------------------------------
# 🌐 Background Async USDT Payout Helper
# -------------------------------------------------------------
async def _async_usdt_payout(bot: Bot, user_id: int, first_name: str, username: str, number: str, amount: float, usd_received: float):
    res = await execute_bep20_usdt_transfer(number, usd_received)

    if res.get('success'):
        tx_hash = res.get('txHash', '')
        tx_link = res.get('txLink', '')

        # ডাটাবেজে উইথড্র কনফার্ম সেভ
        wd_doc = {
            'user_id': user_id, 
            'first_name': first_name, 
            'username': username or "None",
            'method': '🔷 BEP20 (USDT)', 
            'number': number, 
            'amount': amount, 
            'usd_amount': usd_received,
            'tx_hash': tx_hash,
            'status': 'Approved', 
            'date': datetime.datetime.now()
        }
        await withdrawals_col.insert_one(wd_doc)
        await users_col.update_one({'user_id': user_id}, {'$inc': {'pending_withdraw': -amount}})

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
        try:
            await bot.send_message(user_id, user_success_msg, disable_web_page_preview=True)
        except Exception:
            pass

        # ২. মেম্বারের ইনকাম ও টাস্ক হিসাব আনা
        u_data = await users_col.find_one({'user_id': user_id}) or {}
        completed_tasks = u_data.get('completed_tasks', 0)
        ref_income = u_data.get('ref_income', 0.0)
        task_income = u_data.get('total_income', 0.0) - ref_income
        total_income = u_data.get('total_income', 0.0)

        # ৩. পেমেন্ট প্রুফ চ্যানেলে অটো নোটিশ পাঠানো
        channel_proof_msg = (
            '<tg-emoji emoji-id="6253353798928959936">✅</tg-emoji> <b>Withdrawal Approved!</b>\n'
            '━━━━━━━━━━━━━━━━━━━━━━\n'
            f'<tg-emoji emoji-id="5352861489541714456">👤</tg-emoji> <b>User:</b> {first_name} (<code>{user_id}</code>)\n'
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
            await bot.send_message(config.PAYMENT_PROOF_CHANNEL_ID, channel_proof_msg, disable_web_page_preview=True)
        except Exception as err:
            logging.error(f"Channel Proof Error: {err}")

    else:
        # পেমেন্ট ফেইল করলে ম্যানুয়াল রিফান্ড
        err_msg = res.get('error', 'Unknown Error')
        await users_col.update_one({'user_id': user_id}, {'$inc': {'balance': amount, 'pending_withdraw': -amount}})
        try:
            await bot.send_message(user_id, f"⚠️ <b>অটো উইথড্র সফল হয়নি ({err_msg})! আপনার টাকা ব্যালেন্সে ফেরত দেওয়া হয়েছে। এডমিন ম্যানুয়ালি ব্যবস্থা নেবে।</b>")
        except Exception:
            pass

# -------------------------------------------------------------
# 🔘 গ্রুপ এডমিন এপ্রুভ / রিজেক্ট বাটন হ্যান্ডলার
# -------------------------------------------------------------
@router.callback_query(F.data.startswith('gr_wd_'))
async def handle_group_withdraw_buttons(call: types.CallbackQuery, bot: Bot):
    parts = call.data.split('_')
    action = parts[2]
    wd_id = ObjectId(parts[3])
    
    w = await withdrawals_col.find_one({'_id': wd_id})
    if not w or w.get('status') != 'Pending':
        await call.answer("⚠️ এই রিকোয়েস্টটি ইতিমধ্যে প্রসেস করা হয়েছে!", show_alert=True)
        return

    user_id = w['user_id']
    amount = w['amount']
    method = w.get('method', '')
    fee = w.get('fee', 5.00)
    
    if action == 'approve':
        await users_col.update_one({'user_id': user_id}, {'$inc': {'pending_withdraw': -amount}})
        await withdrawals_col.update_one({'_id': wd_id}, {'$set': {'status': 'Approved'}})
        
        await call.message.edit_text(f"{call.message.text}\n\n✅ <b>APPROVED BY ADMIN</b>")
        
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
            await bot.send_message(user_id, approve_user_msg)
        except Exception:
            pass
            
        await call.answer("✅ উইথড্র সফলভাবে এপ্রুভড!", show_alert=True)

        # ম্যানুয়াল পেমেন্ট চ্যানেল প্রুফ পোস্ট
        u_data = await users_col.find_one({'user_id': user_id}) or {}
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
            await bot.send_message(config.PAYMENT_PROOF_CHANNEL_ID, channel_proof_msg)
        except Exception as e:
            logging.error(f"Proof Post Error: {e}")

    elif action == 'reject':
        total_refund = amount + fee
        await users_col.update_one({'user_id': user_id}, {'$inc': {'pending_withdraw': -amount, 'balance': total_refund}})
        await withdrawals_col.update_one({'_id': wd_id}, {'$set': {'status': 'Rejected'}})
        
        await call.message.edit_text(f"{call.message.text}\n\n❌ <b>REJECTED BY ADMIN</b>")
        
        try:
            await bot.send_message(user_id, "আপনার উত্তোলনটি রিজেক্ট করা হয়েছে মনোযোগ দিয়ে কাজ করুন")
        except Exception:
            pass
            
        await call.answer("❌ উইথড্র রিজেক্ট করা হয়েছে!", show_alert=True)
