import asyncio, httpx, os, json
from twscrape import API

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TWITTER_USER = os.environ["TWITTER_USER"]
SUBSCRIBERS_FILE = "subscribers.json"

def load_subscribers():
    if os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE) as f:
            return json.load(f)
    return []

def save_subscribers(subs):
    with open(SUBSCRIBERS_FILE, "w") as f:
        json.dump(subs, f)

async def send_telegram(chat_id, message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    async with httpx.AsyncClient() as client:
        await client.post(url, data={"chat_id": chat_id, "text": message})

async def handle_updates():
    offset = 0
    subscribers = load_subscribers()
    while True:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={offset}&timeout=30"
        async with httpx.AsyncClient(timeout=35) as client:
            r = await client.get(url)
            data = r.json()
        for update in data.get("result", []):
            offset = update["update_id"] + 1
            msg = update.get("message", {})
            text = msg.get("text", "")
            chat_id = msg.get("chat", {}).get("id")
            if text == "/start" and chat_id and chat_id not in subscribers:
                subscribers.append(chat_id)
                save_subscribers(subscribers)
                await send_telegram(chat_id, "✅ Tu es abonné ! Tu recevras les nouveaux tweets.")

async def watch_twitter():
    api = API()
    await api.pool.add_account(
        os.environ["TW_USER"],
        os.environ["TW_PASS"],
        os.environ["TW_EMAIL"],
        os.environ["TW_EMAIL_PASS"]
    )
    await api.pool.login_all()
    last_tweet_id = None
    while True:
        try:
            subscribers = load_subscribers()
            user = await api.user_by_login(TWITTER_USER)
            async for tweet in api.user_tweets(user.id, limit=1):
                if last_tweet_id is None:
                    last_tweet_id = tweet.id
                elif tweet.id != last_tweet_id:
                    last_tweet_id = tweet.id
                    msg = f"🐦 Nouveau tweet de @{TWITTER_USER} :\n\n{tweet.rawContent}\n\nhttps://twitter.com/{TWITTER_USER}/status/{tweet.id}"
                    for chat_id in subscribers:
                        await send_telegram(chat_id, msg)
                break
        except Exception as e:
            print(f"Erreur : {e}")
        await asyncio.sleep(60)

async def main():
    await asyncio.gather(handle_updates(), watch_twitter())

asyncio.run(main())
