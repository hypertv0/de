import requests
from flask import Flask, request, abort, redirect
import os
import time

app = Flask(__name__)

CORS_PROXY_URL = "https://corsproxy.hypercors.workers.dev/?url="

class AdvancedKoolResolver:
    def __init__(self):
        self.session = requests.Session()
        self.ping_url = f"{CORS_PROXY_URL}https://www.dezor.net/api/app/ping"
        # Çözümleme adresi de engelli olabileceğinden, onu da proxy üzerinden çağırıyoruz.
        self.resolve_url = f"{CORS_PROXY_URL}https://kool.to/mediahubmx-resolve.json"
        
        self.headers = {
            "user-agent": "Rokkr/1.8.3 (android)",
            "referer": "https://www.dezor.net/",
            "origin": "https://www.dezor.net",
            "x-requested-with": "com.golge.golgetv2",
            "content-type": "application/json; charset=utf-8"
        }
        
        self.json_data_template = {
            "token": "6rXtO86My-LeiLUMgoXHT8Sw9OHfuiSdMiJgh84-KgAuEh6hXRnFVhCaGJEsA97zD8C4Zf8V4iJRmwXOCjRDKoNeFJsM2NoA2Gmu71_Finswf_S6ZrZRQcvZ0DOgJikVVUumti9a--U-nZJ1iNX2dLHOf5CJ8JJp",
            "reason": "player.enter", "locale": "tr", "theme": "light",
            "metadata": {"device": {"type": "Handset", "brand": "Redmi", "model": "Redmi Note 8 Pro", "name": "Golge", "uniqueId": "2dd6bef695c42221"},"os": {"name": "android", "version": "11"},"app": {"platform": "android", "version": "1.1.2", "buildId": "97245000", "engine": "jsc", "signatures": ["7c8c6b5030a8fa447078231e0f2c0d9ee4f24bb91f1bf9599790a1fafbeef7e0"],"installer": "com.android.vending"},"version": {"package": "net.dezor.browser", "binary": "1.1.2", "js": "1.5.13"}},
            "appFocusTime": 14709, "playerActive": True, "playDuration": 0, "devMode": False, "hasAddon": True, "castConnected": False,
            "package": "net.dezor.browser", "version": "1.5.13", "process": "app"
        }

    def get_auth_signature(self, link):
        """Adım 1: Dezor'dan kimlik doğrulama imzası alır."""
        json_to_send = self.json_data_template.copy()
        json_to_send['url'] = link
        json_to_send['bundle'] = "to.kool.pro"
        current_timestamp = int(time.time() * 1000)
        json_to_send['firstAppStart'] = current_timestamp
        json_to_send['lastAppStart'] = current_timestamp

        try:
            print(f"[*] Adım 1: İmza için Dezor API'sine bağlanılıyor...")
            resp = self.session.post(self.ping_url, json=json_to_send, headers=self.headers, timeout=30)
            
            if resp.status_code != 200:
                print(f"[HATA] Adım 1 Başarısız: Dezor API hata döndü: {resp.status_code} - {resp.text}")
                abort(resp.status_code, f"Adım 1 Başarısız: Dezor API hata döndü: {resp.text}")
            
            signature = resp.json().get("addonSig")
            if not signature:
                print(f"[HATA] Adım 1 Başarısız: API cevabında 'addonSig' bulunamadı.")
                abort(500, "Dezor API'sinden imza (addonSig) alınamadı.")
            
            print(f"[OK] Adım 1 Başarılı: İmza alındı.")
            return signature

        except requests.RequestException as e:
            print(f"[HATA] Adım 1 Başarısız: {e}")
            abort(503, f"Kimlik doğrulama sunucusuna ulaşılamadı: {e}")

    def resolve_kool_link(self, link):
        """Adım 2: Alınan imza ile Kool.to'dan asıl yayın linkini çözer."""
        signature = self.get_auth_signature(link)
        
        resolve_headers = self.headers.copy()
        resolve_headers['mediahubmx-signature'] = signature
        # x-requested-with başlığı bu endpoint için önemli olabilir.
        resolve_headers['x-requested-with'] = 'com.golge.golgetv2'

        resolve_data = { "url": link }
        
        try:
            print(f"[*] Adım 2: İmza ile Kool.to çözümleme sunucusuna bağlanılıyor...")
            resp = self.session.post(self.resolve_url, json=resolve_data, headers=resolve_headers, timeout=30)
            
            if resp.status_code != 200:
                print(f"[HATA] Adım 2 Başarısız: Kool.to API hata döndü: {resp.status_code} - {resp.text}")
                abort(resp.status_code, f"Adım 2 Başarısız: Kool.to API hata döndü: {resp.text}")

            result = resp.json()
            final_url = None
            if isinstance(result, list) and result: final_url = result[0].get("url")
            elif isinstance(result, dict): final_url = result.get("url")
            
            if not final_url:
                print(f"[HATA] Adım 2 Başarısız: API cevabında yayın URL'si bulunamadı.")
                abort(404, "İmza geçerli ancak Kool.to bir yayın adresi döndürmedi.")
            
            print(f"[OK] Adım 2 Başarılı: Nihai yayın linki bulundu.")
            return final_url
        except requests.RequestException as e:
            print(f"[HATA] Adım 2 Başarısız: {e}")
            abort(502, f"Kool.to yayın çözümleme sunucusuna ulaşılamadı: {e}")

# --- Web Sunucusu Uç Noktaları ---
@app.route('/')
def index():
    return "Gelişmiş Kool.to Resolver Aktif.", 200

@app.route('/play/<kool_id>.m3u8')
def play_kool_stream(kool_id):
    original_kool_url = f"https://kool.to/kool-iptv/play/{kool_id}"
    
    resolver = AdvancedKoolResolver()
    final_m3u8_url = resolver.resolve_kool_link(original_kool_url)
    
    print(f"Yönlendirme yapılıyor: {final_m3u8_url}")
    return redirect(final_m3u8_url, code=307)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    # Render'da Start Command ile Gunicorn kullanılacağı için bu blok çalışmaz.
    # Bu sadece yerel testler içindir.
    app.run(host="0.0.0.0", port=port)
