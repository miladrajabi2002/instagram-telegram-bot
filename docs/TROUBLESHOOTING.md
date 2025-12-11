# Troubleshooting Guide

## Login Issues

### Error 403 - "Sorry, there was a problem with your request"

**Cause:** Instagram has blocked or flagged your server's IP address.

**Solutions:**

#### Option 1: Import Session from Browser (RECOMMENDED)

This method bypasses the IP block completely by using a session from your browser.

```bash
bash scripts/login_alternative.sh
# Choose option 1
```

Then follow the interactive prompts to:
1. Login to Instagram in your browser (Chrome/Firefox)
2. Open Developer Tools (F12)
3. Go to Application → Cookies → instagram.com
4. Copy these cookie values:
   - `sessionid`
   - `csrftoken`
   - `ds_user_id`
   - `mid` (optional)
5. Paste them when prompted

**Video tutorial for finding cookies:**
- Chrome: Right-click → Inspect → Application tab → Cookies
- Firefox: Right-click → Inspect → Storage tab → Cookies

#### Option 2: Use Proxy/VPN

Add proxy settings to your `.env` file:

```bash
# HTTP Proxy
PROXY_URL=http://username:password@proxy-server:8080

# Or SOCKS5 Proxy
PROXY_URL=socks5://username:password@proxy-server:1080
```

Then retry:
```bash
bash scripts/login.sh
```

#### Option 3: Login from Different Device

On a device where Instagram doesn't block (your PC/laptop):

```python
from instagrapi import Client

cl = Client()
cl.login('your_username', 'your_password')
# Enter 2FA code if prompted
cl.dump_settings('session.json')
```

Transfer the session file:
```bash
scp session.json user@server:/path/to/bot/sessions/username_session.json
```

#### Option 4: Wait and Retry

Instagram may temporarily block IPs. Wait 24-48 hours and:
- Use Instagram app normally during this time
- Don't attempt automated logins
- Then retry: `bash scripts/login.sh`

---

### 2FA Code Invalid

**Solutions:**
- Ensure code is exactly 6 digits
- Code expires in 30 seconds - enter quickly
- Use latest code from authenticator app
- If using SMS, request new code (option 3 in menu)

---

### Challenge Required

**Solution:**
1. Open Instagram app on phone
2. Complete security verification
3. Wait 10 minutes
4. Retry login

---

## Runtime Issues

### Bot Crashes on Start

**Check logs:**
```bash
tail -f logs/bot.log
```

**Common causes:**
- Missing `.env` file → Run `bash setup.sh`
- Invalid configuration → Check `.env` values
- No session → Run `bash scripts/login.sh`
- Database connection failed → Verify MySQL

---

### Rate Limiting / Action Blocked

**Solution:**

Edit `.env` and reduce limits:
```ini
MAX_FOLLOWS_PER_DAY=10
MAX_FOLLOWS_PER_HOUR=2
MIN_ACTION_DELAY=180
MAX_ACTION_DELAY=900
```

Restart bot:
```bash
bash scripts/run.sh
```

If blocked:
- Stop automation for 24 hours
- Use Instagram normally
- Start with minimal limits

---

### Session Expired

**Solution:**
```bash
rm -rf sessions/*
bash scripts/login.sh
```

Or use alternative login:
```bash
bash scripts/login_alternative.sh
```

---

## Database Issues

### Connection Failed

**Check MySQL is running:**
```bash
sudo systemctl status mysql
```

**Test connection:**
```bash
mysql -u instagram_bot_user -p instagram_bot
```

**Recreate database:**
```bash
mysql -u root -p < sql/schema.sql
```

---

## Telegram Bot Issues

### Bot Not Responding

**Check bot is running:**
```bash
sudo systemctl status instagram-bot
# or
ps aux | grep python | grep main.py
```

**Check Telegram token:**
- Get new token from @BotFather if needed
- Update in `.env`
- Restart bot

**Check admin ID:**
- Get your ID from @userinfobot
- Update `TELEGRAM_ADMIN_ID` in `.env`

---

## Need Help?

If none of these solutions work:

1. **Check full logs:**
   ```bash
   cat logs/bot.log | tail -n 100
   ```

2. **Test configuration:**
   ```bash
   source venv/bin/activate
   python -c "import config; print('Config OK')"
   ```

3. **Verify dependencies:**
   ```bash
   source venv/bin/activate
   pip list | grep instagrapi
   ```

4. **Try from scratch:**
   ```bash
   rm -rf venv sessions
   bash setup.sh
   bash scripts/login_alternative.sh
   ```
