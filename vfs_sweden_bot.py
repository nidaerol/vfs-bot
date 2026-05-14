import time
import requests
import logging
from datetime import datetime

TELEGRAM_TOKEN   = "8982322191:AAHj_JnOTEr3aF38Mlu_iFxu0AD5N2yLlT8"
TELEGRAM_CHAT_ID = "8969917755"
CHECK_INTERVAL_MINUTES = 3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("vfs-bot")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
    "Referer": "https://visa.vfsglobal.com/tur/tr/swe/book-your-appointment",
    "Origin": "https://visa.vfsglobal.com",
}

# VFS Global slot kontrol endpoint'leri
SLOT_URLS = [
    "https://lift.vfsglobal.com/prod/api/v1/appointment/slots?country=Turkey&mission=Sweden&appointmentDate=&visa_type=Schengen+Visa&visa_sub_type=Tourist&center_name=Izmir+Sweden+Visa+Application+Center",
    "https://lift.vfsglobal.com/prod/api/v1/appointment/slots?country=Turkey&mission=Sweden&appointmentDate=&visa_type=Schengen+Visa&visa_sub_type=Tourist&center_name=Istanbul+Sweden+Visa+Application+Center",
    "https://lift.vfsglobal.com/prod/api/v1/appointment/slots?country=Turkey&mission=Sweden&appointmentDate=&visa_type=Schengen+Visa&visa_sub_type=Tourist&center_name=Ankara+Sweden+Visa+Application+Center",
]

CITY_NAMES = ["İzmir", "İstanbul", "Ankara"]

def send_telegram(message: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
        if r.status_code == 200:
            log.info("✅ Telegram mesajı gönderildi.")
        else:
            log.warning(f"Telegram hatası: {r.status_code}")
    except Exception as e:
        log.error(f"Telegram bağlantı hatası: {e}")

def check_slots():
    found = []
    session = requests.Session()
    session.headers.update(HEADERS)

    for url, city in zip(SLOT_URLS, CITY_NAMES):
        try:
            r = session.get(url, timeout=15)
            log.info(f"🔎 {city} — HTTP {r.status_code}")

            if r.status_code == 200:
                data = r.json()
                # Slot verisi varsa ve boş değilse
                if data and data != [] and data != {}:
                    slots_list = data if isinstance(data, list) else data.get("data", [])
                    if slots_list:
                        log.info(f"🎉 {city}'de slot bulundu!")
                        found.append({"city": city, "data": slots_list})
                    else:
                        log.info(f"❌ {city}: slot yok.")
                else:
                    log.info(f"❌ {city}: slot yok.")

            elif r.status_code == 401:
                log.warning(f"⚠️ {city}: Oturum gerekiyor (401). VFS login gerekebilir.")
            else:
                log.warning(f"⚠️ {city}: Beklenmedik yanıt {r.status_code}")

        except Exception as e:
            log.error(f"{city} kontrol hatası: {e}")

    return found

def main():
    log.info("=" * 45)
    log.info("  VFS İsveç Randevu Botu Başlatılıyor")
    log.info("=" * 45)

    send_telegram(
        "🤖 <b>VFS İsveç Randevu Botu Başladı!</b>\n\n"
        f"📍 Takip: İzmir, İstanbul, Ankara\n"
        f"⏱ Her {CHECK_INTERVAL_MINUTES} dakikada kontrol\n\n"
        "Randevu açılınca haber vereceğim! ✈️"
    )

    notified = set()
    check_count = 0

    while True:
        check_count += 1
        log.info(f"\n🔄 Kontrol #{check_count} — {datetime.now().strftime('%d.%m %H:%M')}")

        try:
            slots = check_slots()

            if slots:
                for slot in slots:
                    city = slot["city"]
                    if city not in notified:
                        send_telegram(
                            f"🚨 <b>RANDEVU AÇILDI!</b>\n\n"
                            f"📍 Şehir: <b>{city}</b>\n"
                            f"⏰ Saat: {datetime.now().strftime('%H:%M')}\n\n"
                            f"👉 Hemen gir:\n"
                            f"https://visa.vfsglobal.com/tur/tr/swe/book-your-appointment\n\n"
                            f"⚡ Çok hızlı ol, slotlar saniyeler içinde doluyor!"
                        )
                        notified.add(city)
            else:
                notified.clear()

        except Exception as e:
            log.error(f"Hata: {e}")

        log.info(f"⏳ {CHECK_INTERVAL_MINUTES} dakika bekleniyor...\n")
        time.sleep(CHECK_INTERVAL_MINUTES * 60)

if __name__ == "__main__":
    main()
