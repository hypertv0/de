import requests
from flask import Flask, request, abort, redirect
import os

app = Flask(__name__)

# --- YENİ: Kendi CORS Proxy Adresimiz ---
CORS_PROXY_URL = "https://corsproxy.hypercors.workers.dev/?url="

class DezorKoolResolver:
    def __init__(self):
        self.session = requests.Session()
        # API adresini artık CORS proxy üzerinden çağıracağız
        self.api_url = f"{CORS_PROXY_URL}https://www.dezor.net/api/app/ping"
        
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
            "playerActive": True, "package": "net.dezor.browser", "version": "1.5.13", "process": "app"
        }

    def resolve_kool_link(self, link):
        json_to_send = self.json_data_template.copy()
        json_to_send['url'] = link
        json_to_send['bundle'] = "to.kool.pro"

        try:
            print(f"[*] CORS Proxy üzerinden Dezor API'sine istek gönderiliyor...")
            resp = self.session.post(self.api_url, json=json_to_send, headers=self.headers, timeout=30)
            
            if resp.status_code != 200:
                print(f"[HATA] Dezor API'si (CORS Proxy üzerinden) hata döndü: {resp.status_code} - {resp.text}")
                abort(resp.status_code, f"Dezor API'si hata döndü: {resp.text}")
            
            result = resp.json()
            final_url = result.get("url")
            
            if not final_url:
                print(f"[HATA] API cevabında 'url' bulunamadı: {result}")
                abort(404, "Dezor API'si bir yayın adresi döndürmedi.")
                
            return final_url
            
        except requests.RequestException as e:
            print(f"[HATA] CORS Proxy veya Dezor API'sine bağlanılamadı: {e}")
            abort(503, f"Kimlik doğrulama sunucusuna ulaşılamadı: {e}")

# --- Web Sunucusu Uç Noktaları ---
@app.route('/')
def index():
    return "Kool.to Resolver (CORS Proxy Destekli) Aktif.", 200

@app.route('/play/<kool_id>.m3u8')
def play_kool_stream(kool_id):
    original_kool_url = f"https://kool.to/kool-iptv/play/{kool_id}"
    
    try:
        resolver = DezorKoolResolver()
        final_m3u8_url = resolver.resolve_kool_link(original_kool_url)
        
        print(f"[OK] Link başarıyla çözüldü. Yönlendiriliyor: {final_m3u8_url}")
        
        return redirect(final_m3u8_url, code=307)
        
    except Exception as e:
        # Abort zaten bir cevap oluşturduğu için burada ekstra bir return'e gerek yok.
        pass

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))
    # Render'da Start Command ile Gunicorn kullanılacağı için bu blok çalışmaz.
    app.run(host="0.0.0.0", port=port)
