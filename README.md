# CentrOS.uz — Multi-Tenant Database & Backend Core Arxitekturasi

Bu hujjat **CentrOS.uz** (AI-First Autonomous CRM/ERP) platformasining markaziy ma'lumotlar bazasi, ko'p ijarachili (Multi-Tenant) arxitekturasi, ESP32 IoT xona terminallari bilan MQTT protokoli va kaskadli davomat konveyeri bo'yicha to'liq texnik qo'llanmani taqdim etadi.

---

## 1. Tizim Arxitekturasi va Dasturiy Stack

```mermaid
flowchart TD
    subgraph IoT_Hardware["Sinfxona Apparat Ta'minoti"]
        ESP32["ESP32 MCU (Wi-Fi + RTC)"]
        PN532["PN532 (13.56MHz Mifare NFC)"]
        OLED["0.96' OLED I2C Display"]
        KEYPAD["Touch PIN Keypad"]
        LITTLEFS["LittleFS Offline Buffer"]
        ESP32 --> PN532
        ESP32 --> OLED
        ESP32 --> KEYPAD
        ESP32 --> LITTLEFS
    end

    subgraph MQTT_Broker["Aloqa Qatlami (Broker)"]
        EMQX["Mosquitto / EMQX MQTT Broker (Port 1883)"]
    end

    subgraph Backend_Core["CentrOS.uz Backend (FastAPI + AsyncIO)"]
        MQTT_WORKER["MQTT Ingestion Worker (aiomqtt)"]
        SCHEDULER["APScheduler (Cascade Engine)"]
        REST_API["FastAPI REST & Webhook Endpoints"]
        AUTH["JWT Multi-Tenant Auth"]
        
        REST_API --> AUTH
    end

    subgraph Storage_Layer["Ma'lumotlar Qatlami"]
        PG["PostgreSQL 16 (Row-Level Multi-Tenancy)"]
        REDIS["Redis 7 (Kesh & Queue)"]
    end

    subgraph External_Integrations["Tashqi Integratsiyalar"]
        TELEGRAM["Telegram Bot API (Inline Buttons)"]
        CLICK_PAYME["Click & Payme Merchant API"]
        PHONE_GATEWAY["2-in-1 Phone Gateway (Stoldagi Telefon)"]
        AI_VOICE["Voice AI Pipeline (Groq LPU + Mohir AI)"]
        
        PHONE_GATEWAY -- "SMS yuborish" --> GSM_SMS["Ota-onaga SMS"]
        PHONE_GATEWAY -- "Bluetooth HFP" --> AI_VOICE
    end

    ESP32 -- "Uplink: centros/{tenant}/devices/{uid}/event" --> EMQX
    EMQX -- "Downlink: centros/{tenant}/devices/{uid}/response" --> ESP32
    EMQX <--> MQTT_WORKER
    MQTT_WORKER --> PG
    SCHEDULER --> PG
    SCHEDULER --> TELEGRAM
    SCHEDULER --> AI_VOICE
    REST_API --> PG
    REST_API --> REDIS
    CLICK_PAYME --> REST_API
```

---

## 2. Relyatsion Ma'lumotlar Bazasi Sxemasi (ER Diagram)

Platforma har bir o'quv markazining ma'lumotlarini qat'iy ajratuvchi **Row-Level Tenant Scoping** (`tenant_id` xorijiy kaliti va indeksi) tamoyiliga asoslangan.

```mermaid
erDiagram
    TENANT ||--o{ BRANCH : "filiallari"
    TENANT ||--o{ USER : "xodimlari"
    TENANT ||--o{ COURSE : "kurslari"
    TENANT ||--o{ STUDENT : "o'quvchilari"
    TENANT ||--o{ DEVICE : "terminallari"
    
    BRANCH ||--o{ ROOM : "xonalari"
    ROOM ||--o{ DEVICE : "o'rnatilgan"
    ROOM ||--o{ GROUP : "dars o'tiladi"
    
    COURSE ||--o{ GROUP : "ochilgan"
    TEACHER ||--o{ GROUP : "o'qitadi"
    
    STUDENT ||--o{ STUDENT_CARD : "kartalari"
    STUDENT ||--o{ GROUP_STUDENT : "a'zoligi"
    GROUP ||--o{ GROUP_STUDENT : "tarkibi"
    
    GROUP ||--o{ ATTENDANCE_SESSION : "sessiyalari"
    ATTENDANCE_SESSION ||--o{ ATTENDANCE_LOG : "davomat jurnali"
    STUDENT ||--o{ ATTENDANCE_LOG : "qayd etilgan"
    DEVICE ||--o{ ATTENDANCE_LOG : "skan qilgan"
    
    STUDENT ||--o{ INVOICE : "hisoblari"
    INVOICE ||--o{ PAYMENT : "to'lovlari"
    
    ATTENDANCE_LOG ||--o{ AI_CALL_LOG : "ota-onaga qo'ng'iroq"
```

---

## 3. IoT Terminal (ESP32) va Server O'rtasidagi MQTT Protokoli

Xona terminali va server o'rtasida ma'lumotlar almashinuvi **~50-100 ms** tezlikda MQTT orqali yengil JSON paketlar ko'rinishida amalga oshiriladi.

### A. Uplink (Terminaldan Serverga)
* **Mavzu (Topic):** `centros/{tenant_slug}/devices/{device_uid}/event`
* **JSON namunasi:**
```json
{
  "device_uid": "CENTROS-ESP-B4E62D",
  "rfid_uid": "4A12B89C",
  "pin": null,
  "timestamp": 1730419200,
  "offline_sync": false,
  "battery_level": 95,
  "wifi_rssi": -54
}
```

### B. Downlink (Serverdan Terminalga)
* **Mavzu (Topic):** `centros/{tenant_slug}/devices/{device_uid}/response`
* **Muvaffaqiyatli darsga kirish (Normal check-in):**
```json
{
  "status": "SUCCESS",
  "student_name": "Azizbek R.",
  "group_name": "IELTS Intensive",
  "message": "Xush kelibsiz!",
  "buzzer_tone": "BEEP_SUCCESS",
  "soft_block": false,
  "balance": 150000.0
}
```

* **Moliyaviy Soft-Block (Qarzdorlik holatida):**
```json
{
  "status": "SOFT_BLOCK",
  "student_name": "Jasur A.",
  "message": "Qarzdorlik! Ma'muriyatga!",
  "buzzer_tone": "BEEP_ALERT",
  "soft_block": true,
  "balance": -150000.0
}
```

---

## 4. Kaskadli Davomat Mexanizmi (Cascade Lifecycle)

```mermaid
sequenceDiagram
    autonumber
    actor Student as O'quvchi (Sinfxona)
    participant Terminal as ESP32 Terminal
    participant Backend as CentrOS Backend
    participant Telegram as Telegram Bot
    actor Parent as Ota-ona
    participant VoiceAI as AI Voice Pipeline

    Note over Student, Terminal: Dars boshlandi (14:00)
    Note over Backend: 10 daqiqalik Grace Period (14:10 gacha)
    
    alt O'quvchi kartani bosdi
        Student->>Terminal: RFID karta / PIN kiritildi
        Terminal->>Backend: MQTT check-in event
        Backend-->>Terminal: OLED: "Xush kelibsiz!", BEEP_SUCCESS
        Backend->>Backend: Davomat: PRESENT / LATE
    else Kartani bosmadi (Darsda yo'q)
        Backend->>Backend: 14:10 da ABSENT (PENDING_STAGE1) deb belgilandi
    end

    Note over Backend: Dars tugadi (15:30)
    Backend->>Telegram: 1-Bosqich: Sukutli xabar + Inline tugmalar
    Telegram->>Parent: "Farzandingiz darsda qatnashmadi. Sabab: 1-Kasal, 2-Kechikdi, 3-Boshqa"

    alt Ota-ona Telegramda javob berdi
        Parent->>Telegram: [1-Kasal] tugmasini bosdi
        Telegram->>Backend: Callback Webhook
        Backend->>Backend: Status = EXCUSED, Sabab = KASAL (Yopildi)
    else Ota-ona javob bermadi (18:30 gacha sukut)
        Note over Backend, VoiceAI: 2-Bosqich: Kechki qulay vaqt (18:30 - 20:30)
        Backend->>VoiceAI: Queue AI Voice Call
        VoiceAI->>Parent: Jonli o'zbekcha AI qo'ng'iroq
        Parent-->>VoiceAI: "O'g'lim biroz betob edi, ertaga boradi"
        VoiceAI->>Backend: Post-Call Summary + EXCUSED
    end
```

---

## 5. Loyiha Fayllar Strukturasi

* [**`backend/`**](file:///e:/CentrOS.uz/backend) — FastAPI + SQLAlchemy 2.0 Multi-Tenant Backend Core:
  * [`app/main.py`](file:///e:/CentrOS.uz/backend/app/main.py) — Kirish nuqtasi, MQTT broker ulanishi, kaskadli scheduler va React Frontendni bevosita tarqatish (`StaticFiles`).
  * [`app/models/`](file:///e:/CentrOS.uz/backend/app/models) — Relyatsion sxema: markazlar, filiallar, xonalar, qurilmalar, o'quvchilar, davomat va to'lovlar.
  * [`app/services/attendance_service.py`](file:///e:/CentrOS.uz/backend/app/services/attendance_service.py) — 100 ms kechikishdagi IoT davomat drayveri va moliyaviy Soft-Block.
  * [`app/services/cascade_service.py`](file:///e:/CentrOS.uz/backend/app/services/cascade_service.py) — 3 bosqichli kaskadli ota-onalar aloqasi (Grace period, dars tugagach sukutli SMS/Telegram, kechki AI qo'ng'iroq).
* [**`firmware/`**](file:///e:/CentrOS.uz/firmware) — Sinfxona eshik terminali mikrodasturi (ESP32 DevKit + PN532 Mifare + 0.96" OLED + MAX98357A I2S Audio Dinamik):
  * Klaviaturasiz ixcham korpus, $14-$17 tannarx, LittleFS oflayn kesh, o'zbekcha audio xabarlar.
* [**`voice_agent/`**](file:///e:/CentrOS.uz/voice_agent) — 2-in-1 Telefon Shlyuzi, Groq LPU (Llama 3.3 70B) va Mohir AI Ovozli AI Konveyeri:
  * `phone_bridge.py` — Stoldagi bitta telefon orqali bepul SMS va Bluetooth HFP orqali GSM qo'ng'iroq.
  * `vad.py` — 20 ms freymli VAD va Barge-In (inson gap boshlaganda robotni to'xtatish).
  * `post_call_analytics.py` — Churn xavfini aniqlash va direktorga tezkor Telegram Alert jo'natish.
* [**`frontend/`**](file:///e:/CentrOS.uz/frontend) — React + Vite + TypeScript + Tailwind CSS CRM Paneli va Telegram Mini App:
  * `src/components/TeacherView.tsx` — O'qituvchilar uchun darsda kartasini unutgan o'quvchini 1 bosishda darsda deb belgilash ("Kartasiz darsda").
  * `src/components/DashboardView.tsx` — Direktor uchun BI KPIlar, Churn signallari va sinfxona terminallari monitoringi.
  * `src/components/AICallsView.tsx` — Groq LLM suhbat tahlillari va transkriptlar.
  * `src/components/TelegramMiniAppView.tsx` — Ota-onalar uchun Telegram ichidagi ilova (Davomat, sabab yuborish, Click/Payme to'lov).
  * `src/components/FinanceView.tsx` — Oylik to'lovlar va qarzdorlar nazorati.
* [**`telegram_bot/`**](file:///e:/CentrOS.uz/telegram_bot) — Telegram Bot, Webhook va Polling xizmati:
  * `bot_service.py` — Ota-onalarga dars qoldirilganda inline tugmali xabar yuborish, sababni belgilash (`1-Kasal`, `2-Yo'lda`), o'qituvchilar uchun `/dars` komandasi orqali kartasiz kelgan o'quvchini darsda deb belgilash.
  * `run_polling.py` — Mahalliy kompyuterda domensiz botni to'g'ridan-to'g'ri sinash uchun Long-Polling drayveri.
* [**`start_centros.bat`**](file:///e:/CentrOS.uz/start_centros.bat) — Barcha xizmatlarni (FastAPI + MQTT + React CRM) bitta bosishda ishga tushiruvchi start fayl.
