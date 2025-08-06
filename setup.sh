#!/bin/bash

# نمایش زمان شروع
echo "🔄 شروع نصب - تاریخ و زمان: $(date '+%Y-%m-%d %H:%M:%S %Z')"

# به‌روزرسانی سیستم
echo "🔄 در حال به‌روزرسانی سیستم..."
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv openssh-server curl

# ایجاد محیط مجازی
echo "📦 ایجاد محیط مجازی..."
python3 -m venv venv
source venv/bin/activate

# نصب وابستگی‌ها
echo "📥 نصب وابستگی‌ها..."
pip install -r requirements.txt

# ایجاد دیتابیس
echo "🗄️ ایجاد دیتابیس..."
python3 -c "from database import init_db; init_db()"

# دریافت ورودی‌ها از کاربر
echo "📝 لطفاً اطلاعات زیر را وارد کنید:"
read -p "توکن ربات تلگرام (Bot Token): " bot_token
read -p "Merchant ID زرین‌پال (Zarinpal API): " zarinpal_api
read -p "آدرس کال‌بک (Callback URL، مثلاً https://yourdomain.com): " callback_url
read -p "آیدی عددی ادمین (Admin ID): " admin_id
read -p "نام کاربری ربات (Bot Username، مثلاً @YourBotUsername): " bot_username

# ایجاد فایل config.py
echo "📄 ایجاد فایل تنظیمات..."
cat > config.py << EOL
# این فایل توسط setup.sh تولید شده است
TOKEN = "$bot_token"
ZARINPAL_API = "$zarinpal_api"
CALLBACK_URL = "$callback_url"
ADMIN_ID = $admin_id
BOT_USERNAME = "$bot_username"
EOL

# تنظیم Webhook
echo "🌐 تنظیم Webhook برای ربات..."
webhook_url="${callback_url}/webhook/${bot_token}"
curl -X POST "https://api.telegram.org/bot${bot_token}/setWebhook" -d "url=${webhook_url}" -s > /dev/null
if [ $? -eq 0 ]; then
    echo "✅ Webhook با موفقیت تنظیم شد."
else
    echo "⚠️ خطا در تنظیم Webhook. لطفاً بررسی کنید."
fi

# تنظیم دسترسی SSH
echo "🔒 تنظیم SSH..."
sudo systemctl enable ssh
sudo systemctl start ssh

# باز کردن پورت‌ها در فایروال
echo "🔥 باز کردن پورت‌ها (5000 برای پنل و 8443 برای Webhook)..."
sudo ufw allow 5000
sudo ufw allow 8443
sudo ufw --force enable

# راهنمایی نهایی
echo "✅ نصب کامل شد! لطفاً موارد زیر را بررسی کنید:"
echo "- فایل servers.json را ویرایش کنید (در صورت نیاز)."
echo "- برای اجرا: source venv/bin/activate && python bot.py"
echo "- پنل ادمین: http://your-server-ip:5000/admin"
echo "تاریخ و زمان اتمام: $(date '+%Y-%m-%d %H:%M:%S %Z')"