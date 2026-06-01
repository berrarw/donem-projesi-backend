import os
from flask import Flask, jsonify, request
import firebase_admin
from firebase_admin import credentials, messaging

app = Flask(__name__)

# =================================================================
# 🛠️ FİREBASE ADMİN SDK BAŞLATMA (Girintileri Düzenlenmiş Hali)
# =================================================================
try:
    # Dosya adın tam olarak sol listedeki gibi "firebase_credentials.json" yapıldı
    cred = credentials.Certificate("firebase_credentials.json")
    firebase_admin.initialize_app(cred)
    print("✅ Firebase Admin SDK başarıyla başlatıldı!")
except Exception as e:
    print(f"❌ Firebase Admin SDK başlatılamadı! Hata: {e}")

# =================================================================
# 📣 YENİ: GARANTİLİ PUSH BİLDİRİM FONKSİYONU (TOKEN BAZLI)
# =================================================================
def send_push_notification_to_device(device_token, title, body):
    """
    SERVICE_NOT_AVAILABLE ağ hatasını baypas etmek için sinyali 
    ortak konuya (Topic) değil, doğrudan cihazın kendi FCM Token'ına gönderir.
    """
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            token=device_token,  # Doğrudan hedefe kilitleniyor
        )
        response = messaging.send(message)
        print(f"🚀 Cihaza özel bildirim başarıyla fırlatıldı! Mesaj ID: {response}")
        return True
    except Exception as e:
        print(f"❌ Token bazlı bildirim gönderilirken Firebase hatası: {e}")
        return False

# =================================================================
# 📣 ESKİ: KONU BAZLI BİLDİRİM FONKSİYONU (Yedek Olarak Korundu)
# =================================================================
def send_push_notification_to_topic(topic_name, title, body):
    """Mevcut sistemdeki 'masalar' konusuna genel bildirim yayınlar."""
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            topic=topic_name,
        )
        response = messaging.send(message)
        print(f"📡 Konu ({topic_name}) bildirimi fırlatıldı! Mesaj ID: {response}")
        return True
    except Exception as e:
        print(f"❌ Konu bildirimi gönderilirken Firebase hatası: {e}")
        return False

# =================================================================
# ⚙️ MEVCUT ENDPOINTLER VE SİMÜLASYON VERİLERİ (Aynen Korundu)
# =================================================================

# Örnek Masa Veri Seti (Mevcut projenizdeki mantık temel alınmıştır)
# status -> 0: Müsait, 1: Dolu, 2: Temizlik, 3: Yolda
mock_tables = [
    {"id": 1, "status": 0, "features": "priz, cam_kenari", "res_until": "", "user_type": ""},
    {"id": 2, "status": 1, "features": "priz, sessiz", "res_until": "16:30:00", "user_type": "Öğrenci"},
    {"id": 3, "status": 2, "features": "cam_kenari", "res_until": "", "user_type": ""},
    {"id": 4, "status": 0, "features": "sessiz", "res_until": "", "user_type": ""},
]

@app.route('/masalar/<int:cafe_id>', methods=['GET'])
def get_masalar(cafe_id):
    """Mevcut Flutter uygulamasının saniyede bir çektiği masa listesi."""
    return jsonify({"cafe_id": cafe_id, "masalar": mock_tables}), 200

@app.route('/guncelle/<int:table_id>/<int:new_status>', methods=['PUT', 'POST'])
def guncelle_masa(table_id, new_status):
    """
    Masa durumunu günceller ve masa BOŞALDIĞINDA (status=0) 
    veya rezervasyon yapıldığında tetiklemeyi yapar.
    """
    user_type = request.args.get('user_type', '')
    
    for table in mock_tables:
        if table['id'] == table_id:
            table['status'] = new_status
            table['user_type'] = user_type if new_status != 0 else ""
            if new_status == 0:
                table['res_until'] = ""
                
                # --- TETİKLEME ANI: Masa boşa çıktığında bildirimleri ateşliyoruz ---
                bildirim_baslik = "📣 Masa Boşaldı!"
                bildirim_icerik = f"Masa {table_id} şu an müsait! Hızlı olan kapar."
                
                # 1. Yöntem: Genel Konuya Gönder (Eski Yapın)
                send_push_notification_to_topic("masalar", bildirim_baslik, bildirim_icerik)
                
                # 2. Yöntem: Manuel Test İçin Token Bazlı Gönderim
                # target_token = "FLUTTER_TERMİNALİNDEN_ALDIĞIN_KODU_BURAYA_GEÇİCİ_YAZABİLİRSİN"
                # send_push_notification_to_device(target_token, bildirim_baslik, bildirim_icerik)
                
            return jsonify({"mesaj": f"Masa {table_id} durumu {new_status} olarak güncellendi."}), 200
            
    return jsonify({"hata": "Masa bulunamadı"}), 404

@app.route('/qr-dogrula/<string:qr_data>', methods=['GET'])
def qr_dogrula(qr_data):
    """Mevcut QR kod doğrulama simülasyonu endpoint'i."""
    return jsonify({"mesaj": f"QR Kod ({qr_data}) başarıyla doğrulandı. Masaya girişiniz onaylandı!"}), 200

@app.route('/admin/summary', methods=['GET'])
def admin_summary():
    """Yönetici analiz paneli için grafik verilerini besleyen özet fonksiyonu."""
    total = len(mock_tables)
    occupied = len([m for m in mock_tables if m['status'] == 1])
    
    summary_data = {
        "total_tables": total,
        "occupied_tables": occupied,
        "active_notifications": 1,
        "user_segmentation": {"Öğrenci": 3, "Diğer": 1},
        "feature_analysis": {"priz_tercih": 12, "cam_kenari_tercih": 8, "sessiz_tercih": 5},
        "past_reports": {"Pzt": 45, "Sal": 52, "Çar": 49, "Per": 60, "Cum": 75},
        "hourly_density": {"09": 10, "12": 45, "14": 70, "17": 85, "20": 40}
    }
    return jsonify(summary_data), 200

# =================================================================
# ☁️ CLOUD DEPLOYMENT (BULUT) İÇİN DİNAMİK PORT AYARI
# =================================================================
if __name__ == '__main__':
    # Railway veya Render portu otomatik atar, yereldeyse varsayılan 8000 çalışır.
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port, debug=True)