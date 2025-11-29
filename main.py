import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
import logging
import os
import time

# --- Yapılandırma ---
logging.basicConfig(level=logging.INFO)
app = FastAPI(title="Gelişmiş Kool.to Resolver")

# --- Gelişmiş Dezor/Kool.to Çözümleyici Sınıfı ---
class AdvancedKoolResolver:
    def __init__(self):
        # httpx'in hem senkron hem asenkron istemcilerini kullanacağız
        self.session = httpx.Client(timeout=30.0, follow_redirects=True)
        
        # API adresleri
        self.ping_url = "https://www.dezor.net/api/app/ping"
        self.resolve_url = "https://kool.to/mediahubmx-resolve.json"
        
        # Ping isteği için gönderilecek sabit başlık (header) ve veri (JSON)
        self.ping_headers = {
            "user-agent": "Rokkr/1.8.3 (android)",
            "referer": "https://www.dezor.net/",
            "origin": "https://www.dezor.net",
            "x-requested-with": "com.golge.golgetv2",
            "content-type": "application/json; charset=utf-8",
        }
        self.ping_data_template = {
            "token": "6rXtO86My-LeiLUMgoXHT8Sw9OHfuiSdMiJgh84-KgAuEh6hXRnFVhCaGJEsA97zD8C4Zf8V4iJRmwXOCjRDKoNeFJsM2NoA2Gmu71_Finswf_S6ZrZRQcvZ0DOgJikVVUumti9a--U-nZJ1iNX2dLHOf5CJ8JJp",
            "reason": "player.enter", "locale": "tr", "theme": "light",
            "metadata": {"device": {"type": "Handset", "brand": "Redmi", "model": "Redmi Note 8 Pro", "name": "Golge", "uniqueId": "2dd6bef695c42221"},"os": {"name": "android", "version": "11"},"app": {"platform": "android", "version": "1.1.2", "buildId": "97245000", "engine": "jsc", "signatures": ["7c8c6b5030a8fa447078231e0f2c0d9ee4f24bb91f1bf9599790a1fafbeef7e0"],"installer": "com.android.vending"},"version": {"package": "net.dezor.browser", "binary": "1.1.2", "js": "1.5.13"}},
            "appFocusTime": 14709, "playerActive": True, "playDuration": 0, "devMode": False, "hasAddon": True, "castConnected": False,
            "package": "net.dezor.browser", "version": "1.5.13", "process": "app",
            "firstAppStart": 1741382133336, "lastAppStart": 1741382133336, "ipLocation": None, "adblockEnabled": True,
            "proxy": {"supported": ["ss"], "engine": "ss", "ssVersion": 0, "enabled": True, "autoServer": True, "id": "sg-sgp"},
            "iap": {"supported": False}
        }

    def get_auth_signature(self, link):
        """Adım 1: Dezor'dan kimlik doğrulama imzası alır."""
        json_to_send = self.ping_data_template.copy()
        json_to_send['url'] = link
        json_to_send['bundle'] = "to.kool.pro"
        current_timestamp = int(time.time() * 1000)
        json_to_send['firstAppStart'] = current_timestamp
        json_to_send['lastAppStart'] = current_timestamp

        try:
            logging.info(f"[*] Adım 1: İmza için Dezor API'sine bağlanılıyor...")
            resp = self.session.post(self.ping_url, json=json_to_send, headers=self.ping_headers)
            
            if resp.status_code != 200:
                logging.error(f"[HATA] Adım 1 Başarısız: Dezor API hata döndü: {resp.status_code} - {resp.text}")
                raise HTTPException(status_code=resp.status_code, detail=f"Adım 1 Başarısız: Dezor API hata döndü: {resp.text}")
            
            signature = resp.json().get("addonSig")
            if not signature:
                logging.error(f"[HATA] Adım 1 Başarısız: API cevabında 'addonSig' bulunamadı.")
                raise HTTPException(status_code=500, detail="Dezor API'sinden imza (addonSig) alınamadı.")
            
            logging.info(f"[OK] Adım 1 Başarılı: İmza alındı.")
            return signature
        except requests.RequestException as e:
            logging.error(f"[HATA] Adım 1 Başarısız: {e}")
            raise HTTPException(status_code=503, detail=f"Kimlik doğrulama sunucusuna ulaşılamadı: {e}")

    def resolve_kool_link(self, link):
        """Adım 2: Alınan imza ile Kool.to'dan asıl yayın linkini çözer."""
        signature = self.get_auth_signature(link)
        
        resolve_headers = {
            'mediahubmx-signature': signature,
            'x-requested-with': 'com.golge.golgetv',
            'user-agent': 'Rokkr/1.8.3 (android)',
            'content-type': 'application/json; charset=utf-8',
        }
        resolve_data = { "language": "tr", "region": "TR", "url": link }
        
        try:
            logging.info(f"[*] Adım 2: İmza ile Kool.to çözümleme sunucusuna bağlanılıyor...")
            resp = self.session.post(self.resolve_url, json=resolve_data, headers=resolve_headers)
            
            if resp.status_code != 200:
                logging.error(f"[HATA] Adım 2 Başarısız: Kool.to API hata döndü: {resp.status_code} - {resp.text}")
                raise HTTPException(status_code=resp.status_code, detail=f"Adım 2 Başarısız: Kool.to API hata döndü: {resp.text}")

            result = resp.json()
            final_url = None
            if isinstance(result, list) and result: final_url = result[0].get("url")
            elif isinstance(result, dict): final_url = result.get("url")
            
            if not final_url:
                logging.error(f"[HATA] Adım 2 Başarısız: API cevabında yayın URL'si bulunamadı.")
                raise HTTPException(status_code=404, detail="İmza geçerli ancak Kool.to bir yayın adresi döndürmedi.")
            
            logging.info(f"[OK] Adım 2 Başarılı: Nihai yayın linki bulundu.")
            return final_url
        except requests.RequestException as e:
            logging.error(f"[HATA] Adım 2 Başarısız: {e}")
            raise HTTPException(status_code=502, detail=f"Kool.to yayın çözümleme sunucusuna ulaşılamadı: {e}")

# --- Web Sunucusu Uç Noktaları ---
@app.get("/")
def index():
    return {"mesaj": "Gelişmiş Kool.to Resolver Aktif."}

@app.get("/play/{kool_id}.m3u8", response_class=RedirectResponse)
def play_kool_stream(kool_id: str):
    original_kool_url = f"https://kool.to/kool-iptv/play/{kool_id}"
    
    try:
        resolver = AdvancedKoolResolver()
        final_m3u8_url = resolver.resolve_kool_link(original_kool_url)
        
        logging.info(f"Yönlendirme yapılıyor: {final_m3u8_url}")
        # FastAPI, RedirectResponse'u doğrudan döndürebilir.
        return RedirectResponse(url=final_m3u8_url, status_code=307)
    except HTTPException as e:
        # Resolver içinde fırlatılan HTTPException'ları tekrar fırlat
        raise e
    except Exception as e:
        logging.error(f"Beklenmedik bir hata oluştu: {e}")
        raise HTTPException(status_code=500, detail=f"Sunucuda genel bir hata oluştu: {str(e)}")

# Render'da "Start Command" ile çalıştırılacak
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
