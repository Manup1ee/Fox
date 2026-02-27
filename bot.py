import asyncio, httpx, os, json
import xml.etree.ElementTree as ET

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TWITTER_USER = os.environ["TWITTER_USER"]
SUBSCRIBERS_FILE = "subscribers.json"

NITTER_INSTANCES = [
    "https://nitter.net",
    "https://nitter.privacydev.net",
    "https://nitter.poast.org",
]

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

async def get_latest_tweet():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    async with httpx.AsyncClient(timeout=10, headers=headers) as client:
        for instance in NITTER_INSTANCES:
            try:
                r = await client.get(f"{instance}/{TWITTER_USER}/rss")
                if r.status_code == 200:
                    root = ET.fromstring(r.text)
                    item = root.find(".//item")
                    if item is not None:
                        title = item.findtext("title", "")
                        link = item.findtext("link", "")
                        return title, link
            except Exception:
                continue
    return None, None

async def handle_updates():
    offset = 0
    subscribers = load_subscribers()
    while True:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={offset}&timeout=30"
        try:
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
        except Exception as e:
            print(f"Erreur Telegram : {e}")

async def watch_twitter():
    last_link = None
    while True:
        try:
            title, link = await get_latest_tweet()
            if link and link != last_link:
                if last_link is not None:
                    subscribers = load_subscribers()
                    msg = f"🐦 Nouveau tweet de @{TWITTER_USER} :\n\n{title}\n\n{link}"
                    for chat_id in subscribers:
                        await send_telegram(chat_id, msg)
                last_link = link
        except Exception as e:
            print(f"Erreur : {e}")
        await asyncio.sleep(60)

async def main():
    await asyncio.gather(handle_updates(), watch_twitter())

asyncio.run(main())
