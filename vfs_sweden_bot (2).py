import asyncio
import logging
import os
import requests
from datetime import datetime
from playwright.async_api import async_playwright

TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "8982322191:AAHj_JnOTEr3aF38Mlu_iFxu0AD5N2yLlT8")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "8969917755")

CITIES = ["izmir", "istanbul", "ankara", "antalya"]
CHECK_INTERVAL_MINUTES = 3
VFS_URL = "https://visa.vfsglobal.com/tur/tr/swe/book-your-appointment"
HEADLESS = True

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("vfs_bot.log", encoding="utf-8"),
    ],
)
log = logging.getLogger("vfs-bot")

def send_telegram(message: str) -> bool:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            log.info("✅ Telegram bildirimi gönderildi.")
            return True
        else:
            log.warning(f"Telegram hatası: {r.status_code} — {r.text}")
    except Exception as e:
        log.error(f"Telegram bağlantı hatası: {e}")
    return False

def send_startup_message():
    msg = (
        "🤖 <b>VFS İsveç Randevu Botu Başladı</b>\n\n"
        f"📍 Takip edilen şehirler: {', '.join(c.capitalize() for c in CITIES)}\n"
        f"⏱ Kontrol aralığı: her {CHECK_INTERVAL_MINUTES} dakika\n\n"
        "Randevu bulunduğunda sana haber vereceğim!"
    )
    send_telegram(msg)

async def check_vfs_appointments() -> list:
    found_slots = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=HEADLESS,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="tr-TR",
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()
        try:
            log.info(f"🌐 VFS sayfası açılıyor: {VFS_URL}")
            await page.goto(VFS_URL, wait_until="networkidle", timeout=30_000)
            await asyncio.sleep(3)
            for city in CITIES:
                log.info(f"🔎 {city.capitalize()} kontrol ediliyor...")
                try:
                    city_option = page.locator(f"text={city.capitalize()}").first
                    if await city_option.count() > 0:
                        await city_option.click()
                        await asyncio.sleep(2)
                    no_slot_indicators = [
                        "no appointment", "randevu bulunmuyor",
                        "müsait slot yok", "no slots available", "currently no",
                    ]
                    page_text = (await page.inner_text("body")).lower()
                    slot_available = not any(i in page_text for i in no_slot_indicators)
                    calendar = page.locator(
                        ".mat-calendar, .date-picker, [class*='calendar'], "
                        "[class*='slot'], [class*='available']"
                    )
                    calendar_visible = await calendar.count() > 0
                    if slot_available or calendar_visible:
                        log.info(f"🎉 {city.capitalize()}'de potansiyel slot bulundu!")
                        found_slots.append({
                            "city": city.capitalize(),
                            "url": page.url,
                            "time": datetime.now().strftime("%H:%M"),
                        })
                    else:
                        log.info(f"❌ {city.capitalize()}: slot yok.")
                except Exception as city_err:
                    log.warning(f"⚠️ {city} kontrol hatası: {city_err}")
        except Exception as e:
            log.error(f"Sayfa yükleme hatası: {e}")
        finally:
            await browser.close()
    return found_slots

async def main():
    log.info("=" * 50)
    log.info("  VFS İsveç Randevu Botu Başlatılıyor")
    log.info("=" * 50)
    send_startup_message()
    notified_cities: set = set()
    check_count = 0
    while True:
        check_count += 1
        log.info(f"\n🔄 Kontrol #{check_count} — {datetime.now().strftime('%d.%m %H:%M')}")
        try:
            slots = await check_vfs_appointments()
            if slots:
                for slot in slots:
                    city = slot["city"]
                    if city not in notified_cities:
                        msg = (
                            f"🚨 <b>RANDEVU SLOTU BULUNDU!</b>\n\n"
                            f"📍 Şehir: <b>{city}</b>\n"
                            f"⏰ Saat: {slot['time']}\n"
                            f"🔗 <a href='{slot['url']}'>Hemen Randevu Al!</a>\n\n"
                            f"⚡ Hızlı ol, slotlar saniyeler içinde doluyor!"
                        )
                        send_telegram(msg)
                        notified_cities.add(city)
            else:
                log.info("😴 Hiçbir şehirde slot yok. Bekleniyor...")
                notified_cities.clear()
        except Exception as e:
            log.error(f"Ana döngü hatası: {e}")
            send_telegram(f"⚠️ Bot hatası: {e}\nBot çalışmaya devam ediyor.")
        await asyncio.sleep(CHECK_INTERVAL_MINUTES * 60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("\n🛑 Bot durduruldu.")
        send_telegram("🛑 VFS botu durduruldu.")
