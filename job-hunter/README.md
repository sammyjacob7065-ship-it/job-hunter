# Job Hunter (new repo: job-hunter)
1. Create a NEW GitHub repo `job-hunter`, upload everything in this folder (keep `.github/workflows`).
2. Settings > Secrets > Actions: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GROQ_API_KEY.
3. Actions > hunt > Run workflow (first test). It then runs 20x/day by itself.
4. Telegram message shows a code under the link. Actions > cv > Run workflow > paste the code (or any job link). The tailored PDF comes to Telegram.
Edit config.json to change keywords. Not yet built: auto-email to Gmail, one-tap CV button, login-only sites.

## Buttons + email (step 2)
- Make a NEW bot in BotFather for jobs (job bot). Put ITS token in TELEGRAM_BOT_TOKEN. Send it /start once.
- Import Job_Bot_Buttons.json into n8n, fill the 2 tokens in the Parse Button node, activate, copy the PRODUCTION webhook URL.
- Open in browser: https://api.telegram.org/bot<JOBBOT_TOKEN>/setWebhook?url=<PRODUCTION_WEBHOOK_URL>
- GitHub token: Settings > Developer settings > Fine-grained tokens, repo job-hunter only, Actions: Read and write.
- Email: secrets GMAIL_USER and GMAIL_APP_PASSWORD (Google app password). Keep the repo PRIVATE.
