import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
import aiohttp

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = "8560883661:AAGNtNKl-aDF13-JKogGpEVAvwcwHaB5TeU" # Ваш токен бота
CHAT_ID = "-1004384466442" # Ваш Chat ID группы/канала
SATELLITE_API_KEY = "304b39326bb7bc7ea0b0908246a986a21bf40dcd8d82cf913bd3c7c068692d52" # Ваш Satellite API ключ

# Адрес коллекции Gifts/Usernames
COLLECTION_ADDRESS = "EQCA14o1-VWhS2efqoh_9M1b_A9DtKTuoqfmkn83AbJzwnPi"
MIN_PRICE = 10.0 # Минимальный порог цены в TON/GRAM

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

processed_txs = set()

async def fetch_latest_sales():
    url = f"https://tonapi.io/v2/nfts/collections/{COLLECTION_ADDRESS}/history?limit=20"
    headers = {"Authorization": f"Bearer {SATELLITE_API_KEY}"}
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("events", [])
                else:
                    logging.error(f"Ошибка API: {response.status}")
                    return []
        except Exception as e:
            logging.error(f"Ошибка подключения к сети: {e}")
            return []

async def check_sales():
    while True:
        events = await fetch_latest_sales()
        for event in events:
            event_id = event.get("event_id")
            if not event_id or event_id in processed_txs:
                continue

            # Фильтрация сделок Getgems
            actions = event.get("actions", [])
            for action in actions:
                if action.get("type") == "NftPurchase":
                    purchase = action.get("NftPurchase", {})
                    price_nano = int(purchase.get("amount", 0))
                    price = price_nano / 1e9

                    if price >= MIN_PRICE:
                        nft_name = purchase.get("nft", {}).get("metadata", {}).get("name", "NFT Gift")
                        buyer = purchase.get("buyer", {}).get("address", "Неизвестно")
                        
                        text = (
                            f"🎁 <b>Новая продажа Getgems!</b>\n\n"
                            f"🏷 <b>Товар:</b> {nft_name}\n"
                            f"💰 <b>Цена:</b> {price:.2f} TON/GRAM\n"
                            f"👤 <b>Покупатель:</b> <code>{buyer[:6]}...{buyer[-4:]}</code>\n\n"
                            f"🔗 <a href='https://getgems.io'>Открыть Getgems</a>"
                        )
                        
                        try:
                            await bot.send_message(
                                chat_id=CHAT_ID,
                                text=text,
                                parse_mode=ParseMode.HTML,
                                disable_web_page_preview=True
                            )
                            logging.info(f"Отправлено уведомление для {event_id}")
                        except Exception as e:
                            logging.error(f"Ошибка отправки в Telegram: {e}")

            processed_txs.add(event_id)
            if len(processed_txs) > 1000:
                processed_txs.clear()

        await asyncio.sleep(15)

async def main():
    logging.info("🚀 Бот запущен! Фильтр: сделки от 10.0 GRAM/TON с Getgems...")
    asyncio.create_task(check_sales())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
