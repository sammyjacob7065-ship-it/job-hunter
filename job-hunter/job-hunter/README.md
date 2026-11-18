# Job Hunter (new repo: job-hunter)
1. Create a NEW GitHub repo `job-hunter`, upload everything in this folder (keep `.github/workflows`).
2. Settings > Secrets > Actions: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GROQ_API_KEY.
3. Actions > hunt > Run workflow (first test). It then runs 20x/day by itself.
4. Telegram message shows a code under the link. Actions > cv > Run workflow > paste the code (or any job link). The tailored PDF comes to Telegram.
Edit config.json to change keywords. Not yet built: auto-email to Gmail, one-tap CV button, login-only sites.
