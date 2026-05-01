import os
import re
from fastapi import FastAPI, Request
from telethon import TelegramClient
from telethon.sessions import MemorySession
from telethon.extensions import html

# Vercel Environment Variables se keys fetch karna best practice hai
API_ID = int(os.environ.get("API_ID", 12767104))
API_HASH = os.environ.get("API_HASH", "env me")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN") # Yahan test ke liye daal sakte ho

app = FastAPI()

link_extractor = re.compile(r"(https?://t\.me/[^\s]+)")
c_link_re = re.compile(r"t\.me/c/(\d+)/(\d+)")
pub_link_re = re.compile(r"t\.me/([a-zA-Z0-9_]+)/(\d+)")

@app.post("/webhook")
async def webhook(request: Request):
    update = await request.json()
    
    # Check if update contains a text message
    if "message" not in update or "text" not in update["message"]:
        return {"status": "ok"}
        
    text = update["message"]["text"].strip()
    chat_id = update["message"]["chat"]["id"]
    msg_id = update["message"]["message_id"]

    links = link_extractor.findall(text)
    if not links:
        return {"status": "ok"}

    # Vercel par file save nahi hoti, isliye MemorySession use kar rahe hain
    client = TelegramClient(MemorySession(), API_ID, API_HASH)
    await client.start(bot_token=BOT_TOKEN)

    for raw_link in set(links):
        target_chat = None
        target_msg = None

        m_priv = c_link_re.search(raw_link)
        if m_priv:
            target_chat = int("-100" + m_priv.group(1))
            target_msg = int(m_priv.group(2))
        else:
            m_pub = pub_link_re.search(raw_link)
            if m_pub:
                target_chat = m_pub.group(1)
                target_msg = int(m_pub.group(2))

        if not target_chat or not target_msg:
            continue

        try:
            msg = await client.get_messages(target_chat, ids=target_msg)
            if not msg:
                await client.send_message(chat_id, f"System Error: Message not found for {raw_link}", reply_to=msg_id)
                continue

            original_html = html.unparse(msg.message or "", msg.entities or [])

            tag_and_watermark = f"\n\n<b>Source:</b> {raw_link}\n<b>Developer</b> @lakshitpatidar"
            final_html = f"{original_html}{tag_and_watermark}" if original_html else tag_and_watermark.strip()

            if msg.media:
                await client.send_file(
                    chat_id,
                    msg.media,
                    caption=final_html,
                    parse_mode='html',
                    reply_to=msg_id
                )
            else:
                await client.send_message(
                    chat_id,
                    final_html,
                    parse_mode='html',
                    reply_to=msg_id
                )

        except Exception as e:
            await client.send_message(chat_id, f"System Error on {raw_link}: {e}", reply_to=msg_id)

    # Request puri hone ke baad client disconnect karna padta hai serverless me
    await client.disconnect()
    return {"status": "ok"}

