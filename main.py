import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
import aiohttp

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = "8560883661:AAEDXESyui5_eM8MRJuJpAWFarB_bUfkeeI"
CHAT_ID = "-1004384466442"  # Указан формат с -100 для каналов/групп
SATELLITE_API_KEY = "304b39326bb7bc7ea0b0908246a986a21bf40dcd8d82cf913bd3c7c068692d52"

# Адрес коллекции Gifts/Usernames
COLLECTION_ADDRESS = "EQCA14o1-VWhS2efqoh_9M1b_A9DtKTuoqfmkn83AbJzwnPi"
MIN_PRICE = 10.0  # Минимальный порог цены в TON/GRAM

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

processed_txs = set()

async def fetch_latest_sales():
    # Используем публичный v2 эндпоинт TonAPI для событий коллекции
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

            actions = event.get("actions", [])
            for action in actions:
                if action.get("type") == "NftPurchase":
                    purchase = action.get("NftPurchase", {})
                    price_nano = int(purchase.get("amount", 0))
                    price = price_nano / 1e9

                    if price >= MIN_PRICE:
                        nft_name = purchase.get("nft", {}).get("metadata", {}).get("name", "NFT Gift")
                        buyer = purchase.get("buyer", {}).get("address", "Неизвестно")
                        
                        # Фильтрация площадки (Getgems vs Telegram Market / Fragment)
                        marketplace = purchase.get("marketplace", {}).get("name", "").lower()
                        
                        if "fragment" in marketplace or "telegram" in marketplace:
                            platform_name = "Telegram Market"
                            link = "https://fragment.com"
                        else:
                            platform_name = "Getgems"
                            link = "https://getgems.io"

                        buyer_fmt = f"{buyer[:6]}...{buyer[-4:]}" if len(buyer) > 10 else buyer

                        text = (
                            f"🎁 <b>Новая продажа ({platform_name})!</b>\n\n"
                            f"🏷 <b>Товар:</b> {nft_name}\n"
                            f"💰 <b>Цена:</b> {price:.2f} TON/GRAM\n"
                            f"👤 <b>Покупатель:</b> <code>{buyer_fmt}</code>\n\n"
                            f"🔗 <a href='{link}'>Открыть {platform_name}</a>"
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
    logging.info("🚀 Бот запущен! Отслеживание Getgems & Telegram Market от 10 TON/GRAM...")
    asyncio.create_task(check_sales())
    # Игнорируем накопленные старые апдейты для исключения конфликтов
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
