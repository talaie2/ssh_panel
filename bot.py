from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from database import init_db, add_user, get_user_info, add_request, get_pending_requests, update_request_status, get_users, update_server_list
from ssh_manager import create_ssh_user
import json
import requests
from datetime import datetime
import config
from flask import Flask, request, render_template, redirect, url_for

def load_servers():
    try:
        with open('servers.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        default_servers = [{"host": "venus", "port": 4646, "country": "🇨🇭"}, {"host": "coral", "port": 4141, "country": "🇦🇪"}, {"host": "luna", "port": 3131, "country": "🇩🇪"}]
        with open('servers.json', 'w') as f:
            json.dump(default_servers, f)
        return default_servers

servers = load_servers()

app = Flask(__name__, template_folder='templates')

main_keyboard = [[InlineKeyboardButton("📋 اطلاعات اکانت", callback_data='info')], [InlineKeyboardButton("🛒 خرید اکانت", callback_data='buy')], [InlineKeyboardButton("💬 پشتیبانی", callback_data='support')]]
main_reply_markup = InlineKeyboardMarkup(main_keyboard)

def get_buy_keyboard():
    return [[InlineKeyboardButton(f"{server['country']} {server['host']}:{server['port']}", callback_data=f"buy_{i}") for i, server in enumerate(servers)]] + [[InlineKeyboardButton("💳 کارت به کارت", callback_data='card_to_card')]]

buy_reply_markup = InlineKeyboardMarkup(get_buy_keyboard())

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎉 به ربات SSH خوش آمدید!\n📡 لیست سرورها:\n" + "\n".join([f"{server['country']} {server['host']}:{server['port']}" for server in servers]) + "\n\nاز منو استفاده کنید!", reply_markup=main_reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'info':
        user_id = query.from_user.id
        user_info = get_user_info(user_id)
        if user_info:
            await query.edit_message_text(f"ℹ️ اطلاعات اکانت:\nنام: {user_info['username']}\nرمز: {user_info['password']}\nانقضا: {user_info['expiry_date']}\nسرور: {user_info['host']}:{user_info['port']}")
        else:
            await query.edit_message_text("⛔ اکانت ندارید. لطفاً خرید کنید!")
    elif query.data == 'buy':
        await query.edit_message_text("🛒 سرور را انتخاب کنید یا کارت به کارت استفاده کنید:", reply_markup=buy_reply_markup)
    elif query.data.startswith('buy_'):
        server_index = int(query.data.split('_')[1])
        selected_server = servers[server_index]
        price = 50000
        response = requests.post("https://api.zarinpal.com/pg/v4/payment/request.json", json={"merchant_id": config.ZARINPAL_API, "amount": price, "description": f"خرید اکانت SSH - {selected_server['host']}", "callback_url": config.CALLBACK_URL})
        data = response.json()['data']
        if data.get('code') == 100:
            payment_url = f"https://www.zarinpal.com/pg/StartPay/{data['authority']}"
            context.user_data['authority'] = data['authority']
            context.user_data['server'] = selected_server
            await query.edit_message_text(f"💸 پرداخت: {payment_url}")
        else:
            await query.edit_message_text("❌ خطا در پرداخت!")
    elif query.data == 'card_to_card':
        context.user_data['waiting_for_photo'] = True
        await query.edit_message_text("📸 اسکرین‌شات تراکنش را ارسال کنید:\nشماره کارت: 6037-XXXX-XXXX-XXXX")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('waiting_for_photo'):
        photo = update.message.photo[-1]
        user_id = update.message.from_user.id
        add_request(user_id, -1, photo.file_id)
        await update.message.reply_text("✅ درخواست ثبت شد. منتظر تأیید باشید.")
        context.user_data.pop('waiting_for_photo')
        await context.bot.send_message(config.ADMIN_ID, f"🔔 درخواست جدید: کاربر {user_id}\nتأیید با /approve_{update.message.message_id}")

async def approve_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.chat_id == config.ADMIN_ID and update.message.text.startswith('/approve_'):
        request_id = int(update.message.text.split('_')[1])
        update_request_status(request_id, 'approved')
        conn = sqlite3.connect('ssh_panel.db')
        c = conn.cursor()
        c.execute("SELECT user_id, server_index FROM requests WHERE id = ? AND status = 'approved'", (request_id,))
        request = c.fetchone()
        conn.close()
        if request:
            user_id, server_index = request
            selected_server = servers[0] if server_index == -1 else servers[server_index]
            username = f"user_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            password = "random_password"
            create_ssh_user(username, password, 1)
            add_user(username, password, 30, 1, selected_server['host'], selected_server['port'])
            await context.bot.send_message(user_id, f"✅ اکانت:\nنام: {username}\nرمز: {password}\nسرور: {selected_server['host']}:{selected_server['port']}\nمدت: 30 روز")
            await update.message.reply_text(f"✅ اکانت برای {user_id} ارسال شد.")

@app.route(f'/webhook/{config.TOKEN}', methods=['POST'])
async def webhook(request):
    update = Update.de_json(request.get_json(), application.bot)
    await application.process_update(update)
    return 'OK', 200

@app.route('/admin')
def admin_dashboard():
    conn = sqlite3.connect('ssh_panel.db')
    c = conn.cursor()
    c.execute("SELECT username, password, expiry_date, host, port FROM users")
    users = c.fetchall()
    c.execute("SELECT id, user_id, created_at, photo_id FROM requests WHERE status = 'pending'")
    requests = c.fetchall()
    c.execute("SELECT COUNT(*) FROM users")
    user_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM requests WHERE status = 'pending'")
    request_count = c.fetchone()[0]
    conn.close()
    return render_template('admin.html', users=users, requests=requests, user_count=user_count, request_count=request_count, servers=servers)

@app.route('/approve/<int:request_id>', methods=['POST'])
def approve_request_web(request_id):
    update_request_status(request_id, 'approved')
    conn = sqlite3.connect('ssh_panel.db')
    c = conn.cursor()
    c.execute("SELECT user_id, server_index FROM requests WHERE id = ? AND status = 'approved'", (request_id,))
    request = c.fetchone()
    conn.close()
    if request:
        user_id, server_index = request
        selected_server = servers[0] if server_index == -1 else servers[server_index]
        username = f"user_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        password = "random_password"
        create_ssh_user(username, password, 1)
        add_user(username, password, 30, 1, selected_server['host'], selected_server['port'])
        application.bot.send_message(user_id, f"✅ اکانت:\nنام: {username}\nرمز: {password}\nسرور: {selected_server['host']}:{selected_server['port']}\nمدت: 30 روز")
    return redirect(url_for('admin_dashboard'))

@app.route('/reject/<int:request_id>', methods=['POST'])
def reject_request_web(request_id):
    update_request_status(request_id, 'rejected')
    return redirect(url_for('admin_dashboard'))

@app.route('/update_server', methods=['POST'])
def update_server():
    host = request.form['host']
    port = int(request.form['port'])
    country = request.form['country']
    new_server = {"host": host, "port": port, "country": country}
    servers.append(new_server)
    update_server_list(servers)
    return redirect(url_for('admin_dashboard'))

application = Application.builder().token(config.TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(CallbackQueryHandler(button))
application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
application.add_handler(CommandHandler("approve_", approve_request))

if __name__ == '__main__':
    init_db()
    application.run_webhook(listen='0.0.0.0', port=8443, url_path=config.TOKEN, webhook_url=f"https://{config.CALLBACK_URL.split('//')[1]}/webhook/{config.TOKEN}")
    app.run(host='0.0.0.0', port=5000)