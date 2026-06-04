import streamlit as st
from streamlit_autorefresh import st_autorefresh
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import time
import os
import requests

# ==========================================
# 1. SAYFA AYARLARI VE ARAYÜZ TASARIMI
# ==========================================
st.set_page_config(layout="wide", page_title="BIST & KÜRESEL HİBRİT KOMUTA MERKEZİ")

# UI/UX OPTİMİZASYONU
st.markdown("""
    <style>
    .main, .stApp { background-color: #FDFCF0 !important; }
    section[data-testid="stSidebar"] { background-color: #F0EDE0 !important; border-right: 1px solid #D1D1D1; }
    p, span, label, .stMarkdown { color: #000000 !important; font-weight: 700 !important; font-size: 1.1rem !important; }
    h1, h2, h3 { color: #1A1A1A !important; font-weight: 900 !important; border-bottom: 2px solid #1A1A1A !important; padding-bottom: 10px; }
    
    .stMetric { background-color: #FFFFFF !important; padding: 10px 5px !important; border-radius: 10px !important; border: 1px solid #CCCCCC !important; box-shadow: 2px 2px 5px rgba(0,0,0,0.05) !important; }
    
    [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] > div { 
        color: #555555 !important;
        font-weight: 800 !important; white-space: normal !important; 
        word-wrap: break-word !important; overflow: visible !important; text-overflow: clip !important; 
        font-size: 0.75rem !important;
        line-height: 1.2 !important;
    }
    
    [data-testid="stMetricValue"], [data-testid="stMetricValue"] > div { 
        color: #000000 !important;
        font-weight: 900 !important; font-size: 1.15rem !important; 
        white-space: normal !important; overflow: visible !important; text-overflow: clip !important;
    }
    
    [data-testid="stMetricDelta"] { font-size: 0.80rem !important; }
    
    .ai-score-box {
        background: linear-gradient(135deg, #1A1A1A 0%, #2A2A2A 100%);
        color: white !important; padding: 20px; border-radius: 15px; border: 1px solid #444;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2); margin-top: 20px; margin-bottom: 20px;
    }
    .ai-score-box h2 { color: #FFD700 !important; border: none !important; margin-bottom: 5px; }
    .ai-score-box h1 { color: #FFFFFF !important; font-size: 3rem !important; margin-top: 0; border: none !important; margin-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ BIST & KÜRESEL ÇİFT YÖNLÜ KOMUTA MERKEZİ")

# ==========================================
# 2. YAN MENÜ: ANA ŞALTER
# ==========================================
with st.sidebar:
    st.markdown("### 🎛️ SENSÖR MODU")
    calisma_modu = st.sidebar.radio("Sistemi Seçin:", [
        "Lazer (Detaylı Analiz & Strateji)", 
        "Radar (BIST 100 Full Hibrit Tarama)",
        "Forex & Küresel Piyasalar (Çift Yönlü)",
        "Ultra FXMatik (Quant Matrix)"
    ])
    st.markdown("---")
    
# FOREX VE KÜRESEL PİYASALAR SÖZLÜĞÜ
forex_assets = {
    "ONS ALTIN": "GC=F",
    "ONS GÜMÜŞ": "SI=F",
    "ONS BAKIR" : "HG=F",
    "ONS PALADYUM": "PA=F",
    "ONS PLATİN": "PL=F",
    "BRENT PETROL": "BZ=F",
    "WTI HAM PETROL": "CL=F",
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "USD/JPY": "USDJPY=X",
    "S&P 500": "^GSPC",
    "NASDAQ 100": "^NDX",
    "DXY (Dolar Endeksi)": "DX-Y.NYB",
    "DAX 40 (Almanya)": "^GDAXI",
    "ETH/USD": "ETH-USD",
    "BTC/USD": "BTC-USD"
}

# =================================================================================
# 🚀 ANLIK CANLI VERİ ENJEKTÖRÜ (YAHOO REALTIME ENDPOINT)
# =================================================================================
def get_realtime_data_direct(ticker_sembol, interval_kod):
    """
    Kütüphane gecikmelerini atlayarak doğrudan Yahoo Canlı Veri sunucularına
    bağlanır ve anlığa en yakın dataframe çıktısını üretir.
    """
    # Süre kilitlerini periyoda göre optimize ediyoruz
    range_map = {"15m": "5d", "1h": "30d", "1d": "2y"}
    sure_kilit = range_map.get(interval_kod, "2y")
    
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker_sembol}"
    params = {"range": sure_kilit, "interval": interval_kod, "includePrePost": "false"}
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        req = requests.get(url, params=params, headers=headers, timeout=10)
        if req.status_code == 200:
            json_data = req.json()
            result = json_data['chart']['result'][0]
            timestamps = result['timestamp']
            indicators = result['indicators']['quote'][0]
            
            df_rt = pd.DataFrame({
                'Open': indicators['open'],
                'High': indicators['high'],
                'Low': indicators['low'],
                'Close': indicators['close'],
                'Volume': indicators['volume']
            }, index=pd.to_datetime(timestamps, unit='s'))
            
            # Hatalı boş satırları temizleme geometrisi
            df_rt.dropna(subset=['Close'], inplace=True)
            return df_rt
    except:
        pass
    return pd.DataFrame()

# =================================================================================
# ÇEKİRDEK 1: LAZER MODU (ANLIK ENJEKTÖRLÜ CANLI SÜRÜM)
# =================================================================================
if calisma_modu == "Lazer (Detaylı Analiz & Strateji)":
    # Anlık takip için ekran yenileme hızını 10 saniyeye çekiyoruz
    st_autorefresh(interval=10000, limit=2000, key="lazer_canli_guncelleme_fixed_v2")
    
    import threading

    with st.sidebar:
        st.markdown("### ⚙️ HİSSE PARAMETRELERİ")
        hisse = st.text_input("HİSSE KODU", "THYAO.IS").upper().strip()
        zaman_sozlugu = {"15 Dakika": "15m", "1 Saat": "1h", "1 Gün": "1d"}
        secilen_int = st.selectbox("VERİ SIKLIĞI", list(zaman_sozlugu.keys()), index=2)
        view_period = st.selectbox("GÖRÜNÜM ARALIĞI", ["1 Ay", "3 Ay", "6 Ay", "1 Yıl", "Tümü"], index=2)

    # -----------------------------------------------------------------------------
    # TELEGRAM ENTEGRASYON BÖLÜMÜ
    # -----------------------------------------------------------------------------
    TELEGRAM_BOT_TOKEN = "8817119197:AAHcHADLXZ7DbLgJp7yskg94QO0Q6jJd85s"
    TELEGRAM_CHAT_ID = "1338802399"

    def telegram_bist_sinyal_gonder(mesaj):
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            try:
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mesaj, "parse_mode": "Markdown"}
                requests.post(url, json=payload, timeout=5)
            except Exception as e:
                pass

    # -----------------------------------------------------------------------------
    # 🛰️ OTONOM ARKA PLAN RADAR MOTORU
    # -----------------------------------------------------------------------------
    bist100_otonom_liste = [
        "AEFES.IS", "AGHOL.IS", "AKBNK.IS", "AKCNS.IS", "AKFGY.IS", "AKSA.IS", "AKSEN.IS", "ALARK.IS", "ALBRK.IS", 
        "ALFAS.IS", "ARCLK.IS", "ASELS.IS", "ASTOR.IS", "ASUZU.IS", "AYDEM.IS", "AYGAZ.IS", "BAGFS.IS", "BERA.IS", 
        "BIENY.IS", "BIMAS.IS", "BRISA.IS", "BRSAN.IS", "BUCIM.IS", "CANTE.IS", "CCOLA.IS", "CIMSA.IS", "CWENE.IS", 
        "DOAS.IS", "DOHOL.IS", "EGEEN.IS", "ECILC.IS", "EKGYO.IS", "ENERY.IS", "ENJSA.IS", "ENKAI.IS", "EREGL.IS", 
        "EUREN.IS", "EUPWR.IS", "FROTO.IS", "GARAN.IS", "GENIL.IS", "GESAN.IS", "GLYHO.IS", "GUBRF.IS", "GWIND.IS", 
        "HALKB.IS", "HEKTS.IS", "HKTM.IS", "HLGYO.IS", "IMASM.IS", "IPEKE.IS", "ISCTR.IS", "ISDMR.IS", "ISGYO.IS", 
        "ISMEN.IS", "IZENR.IS", "KALES.IS", "KARSN.IS", "KCAER.IS", "KCHOL.IS", "KMPUR.IS", "KONTR.IS", "KONYA.IS", 
        "KOZAA.IS", "KOZAL.IS", "KRDMD.IS", "KZBGY.IS", "MAVI.IS", "MGROS.IS", "MIATK.IS", "ODAS.IS", "OTKAR.IS", 
        "OYAKC.IS", "PENTA.IS", "PETKM.IS", "PGSUS.IS", "PNLSN.IS", "QUAGR.IS", "SAHOL.IS", "SASA.IS", "SDTTR.IS", 
        "SISE.IS", "SMRTG.IS", "SOKM.IS", "TABGD.IS", "TAVHL.IS", "TCELL.IS", "THYAO.IS", "TKFEN.IS", "TOASO.IS", 
        "TSKB.IS", "TTKOM.IS", "TTRAK.IS", "TUKAS.IS", "TUPRS.IS", "ULKER.IS", "VAKBN.IS", "VESBE.IS", "VESTL.IS", 
        "YKBNK.IS", "YYLGD.IS", "ZOREN.IS"
    ]

    if not hasattr(st, "_otonom_hafiza"): st._otonom_hafiza = {}
    if "otonom_radar_aktif" not in st.session_state: st.session_state.otonom_radar_aktif = False

    def saf_arka_plan_tarayici():
        while True:
            for o_kod in bist100_otonom_liste:
                try:
                    df_o = get_realtime_data_direct(o_kod, "1d")
                    if df_o.empty or len(df_o) < 5: continue

                    df_o['EMA50'] = df_o['Close'].ewm(span=50, adjust=False).mean()
                    delta_o = df_o['Close'].diff()
                    gain_o = delta_o.clip(lower=0)
                    loss_o = -delta_o.clip(upper=0)
                    rsi_o = 100 - (100 / (1 + (gain_o.ewm(com=13, adjust=False).mean() / loss_o.ewm(com=13, adjust=False).mean()))).iloc[-1].item()
                    
                    fiyat_o = df_o['Close'].iloc[-1].item()
                    ticker_o = yf.Ticker(o_kod)
                    info_o = ticker_o.info
                    fk_o = info_o.get('trailingPE', None)
                    pddd_o = info_o.get('priceToBook', None)
                    roe_o = info_o.get('returnOnEquity', None)
                    favok_o = info_o.get('ebitdaMargins', None)

                    o_puan = 0.0
                    o_maddeler = []

                    if isinstance(fk_o, float) and 0 < fk_o < 15: 
                        o_puan += 1.0
                        o_maddeler.append(f"📊 F/K Oranı Makul ({fk_o:.2f})")
                    if isinstance(pddd_o, float) and 0 < pddd_o < 3.5: 
                        o_puan += 1.0
                        o_maddeler.append(f"📑 Defter Değeri Dengeli ({pddd_o:.2f})")
                    if roe_o and roe_o > 0.30: 
                        o_puan += 1.5
                        o_maddeler.append(f"💰 Mükemmel Özsermaye Kârlılığı (%{roe_o*100:.1f})")
                    if favok_o and favok_o > 0.15: 
                        o_puan += 1.0
                        o_maddeler.append(f"🏭 Güçlü Operasyonel Kâr (%{favok_o*100:.1f})")
                    if 30 <= rsi_o <= 45: 
                        o_puan += 2.0
                        o_maddeler.append(f"🎯 RSI Toplama Bölgesinde ({rsi_o:.1f})")
                    elif rsi_o < 30: 
                        o_puan += 1.5
                        o_maddeler.append(f"🔥 Aşırı Satım Bölgesi ({rsi_o:.1f})")
                    if fiyat_o > df_o['EMA50'].iloc[-1]: 
                        o_puan += 1.0
                        o_maddeler.append("📈 EMA Trend Gücü Üstün")

                    o_puan = min(10.0, max(0.0, round(o_puan, 1)))
                    hisse_temiz = o_kod.replace('.IS', '')

                    if o_puan >= 7.0:
                        simdi = time.time()
                        son_atim_zamani = st._otonom_hafiza.get(hisse_temiz, 0.0)
                        if (simdi - son_atim_zamani) > 3600.0:
                            st._otonom_hafiza[hisse_temiz] = simdi
                            gerekce_metni = "\n".join(o_maddeler)
                            
                            radar_mesaj = (
                                f"🛰️ *BIST 100 OTONOM RADAR SİNYALİ*\n\n"
                                f"**Hisse:** #{hisse_temiz}\n"
                                f"**Anlık Fiyat:** `{fiyat_o:.2f} TL`\n"
                                f"**Yapar Zeka Skoru:** `{o_puan} / 10` 🔥\n\n"
                                f"**🔍 Tespit Edilen Güçlü Gerekçeler:**\n{gerekce_metni}"
                            )
                            telegram_bist_sinyal_gonder(radar_mesaj)
                    time.sleep(3.5)
                except:
                    time.sleep(4)
            time.sleep(15)

    if not st.session_state.otonom_radar_aktif:
        t = threading.Thread(target=saf_arka_plan_tarayici, daemon=True)
        t.start()
        st.session_state.otonom_radar_aktif = True

    # Manuel Ekran Hafıza Kilitleri
    state_sinyal_key = f"bist_hybrid_state_{hisse}"
    state_fiyat_key = f"bist_hybrid_price_{hisse}"
    state_zaman_key = f"bist_hybrid_time_{hisse}"
    
    if state_sinyal_key not in st.session_state: st.session_state[state_sinyal_key] = "NÖTR (İZLE)"
    if state_fiyat_key not in st.session_state: st.session_state[state_fiyat_key] = 0.0
    if state_zaman_key not in st.session_state: st.session_state[state_zaman_key] = 0.0
        
    # Anlık veri akışı için önbellek süresini (ttl) kaldırıyor ya da minimalize ediyoruz
    @st.cache_data(ttl=1, show_spinner=False)
    def get_full_data(kod, interval):
        for deneme in range(3):
            try:
                # Gecikmeli kütüphane fonksiyonu yerine doğrudan anlık veri motoruna bağlanıyoruz
                data = get_realtime_data_direct(kod, interval)
                ticker = yf.Ticker(kod)
                info = ticker.info
                
                if not data.empty:
                    if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
                    data.columns = [str(c).strip().capitalize() for c in data.columns]
                    
                    try:
                        if data.index.tzinfo is None:
                            if interval != "1d" and len(data.index) > 0: 
                                data.index = data.index.tz_localize('UTC').tz_convert('Europe/Istanbul')
                        else:
                            data.index = data.index.tz_convert('Europe/Istanbul')
                    except: pass
                    return data, info
            except Exception as e:
                time.sleep(1.0)
        return pd.DataFrame(), {}

    @st.cache_data(ttl=3600, show_spinner=False)
    def otonom_sektor_hesapla(hisse_kodu):
        sektorler = {
            "HAVACILIK": ["THYAO.IS", "PGSUS.IS", "TAVHL.IS", "CLEBI.IS", "DOCO.IS"],
            "BANKACILIK": ["AKBNK.IS", "GARAN.IS", "ISCTR.IS", "YKBNK.IS", "HALKB.IS", "VAKBN.IS", "ALBRK.IS", "SKBNK.IS", "TSKB.IS"],
            "OTOMOTİV & YAN SANAYİ": ["FROTO.IS", "TOASO.IS", "DOAS.IS", "KARSN.IS", "ASUZU.IS", "TTRAK.IS", "OTKAR.IS", "BRISA.IS", "EGEEN.IS"],
            "ENERJİ & GAZ": ["ENJSA.IS", "ASTOR.IS", "AKSEN.IS", "GWIND.IS", "SMRTG.IS", "ALFAS.IS", "CWENE.IS", "EUPWR.IS", "HUNER.IS", "ZOREN.IS", "ODAS.IS", "CANTE.IS", "AYDEM.IS", "GESAN.IS", "KARYE.IS", "NATEN.IS", "ENERY.IS", "IZENR.IS", "AYGAZ.IS", "CONSE.IS", "MAGEN.IS", "ESEN.IS", "BIOEN.IS", "CATES.IS"],
            "HOLDİNG & YATIRIM": ["KCHOL.IS", "SAHOL.IS", "ALARK.IS", "DOHOL.IS", "AGHOL.IS", "TKFEN.IS", "ENKAI.IS", "NTHOL.IS", "BERA.IS", "GLYHO.IS"],
            "DEMİR-ÇELİK": ["EREGL.IS", "KRDMD.IS", "ISDMR.IS", "KCAER.IS", "BRSAN.IS", "CEMAS.IS"],
            "PERAKENDE & TİCARET": ["BIMAS.IS", "MGROS.IS", "SOKM.IS", "CRFSA.IS", "MAVI.IS"],
            "ÇİMENTO & CAM & SERAMİK": ["AKCNS.IS", "CIMSA.IS", "OYAKC.IS", "BUCIM.IS", "BTCIM.IS", "BIENY.IS", "KALES.IS", "QUAGR.IS", "SISE.IS", "KONYA.IS"],
            "TELEKOMÜNİKASYON": ["TCELL.IS", "TTKOM.IS"],
            "GIDA & İÇECEK": ["CCOLA.IS", "AEFES.IS", "ULKER.IS", "TABGD.IS", "TUKAS.IS", "TATGD.IS", "PETUN.IS", "YYLGD.IS"],
            "TEKNOLOJİ & BİLİŞİM": ["HKTM.IS", "KONTR.IS", "MIATK.IS", "PENTA.IS", "ARDYZ.IS", "VBTYZ.IS", "MTRKS.IS"],
            "SAVUNMA SANAYİ": ["ASELS.IS", "SDTTR.IS"],
            "KİMYA & PETROKİMYA & GÜBRE": ["AKSA.IS", "BAGFS.IS", "GUBRF.IS", "HEKTS.IS", "KMPUR.IS", "PETKM.IS", "SASA.IS", "TUPRS.IS"],
            "GAYRİMENKUL YATIRIM (GYO)": ["AKFGY.IS", "EKGYO.IS", "HLGYO.IS", "ISGYO.IS", "KZBGY.IS", "TRGYO.IS"],
            "MADENCİLİK": ["IPEKE.IS", "KOZAA.IS", "KOZAL.IS", "PRKME.IS"],
            "DAYANIKLI TÜKETİM & ELEKTRONİK": ["ARCLK.IS", "VESBE.IS", "VESTL.IS"],
            "İLAÇ & SAĞLIK": ["ECILC.IS", "GENIL.IS", "DEVA.IS", "MPARK.IS", "LKMNH.IS"],
            "ARACI KURUMLAR & FİNANS": ["ISMEN.IS", "INFO.IS"],
            "İNŞAAT MALZEMELERİ & İMALAT": ["EUREN.IS", "IMASM.IS", "PNLSN.IS"]
        }
        
        bulunan_sektor = None
        for sektor_adi, hisseler in sektorler.items():
            if hisse_kodu in hisseler:
                bulunan_sektor = sektor_adi
                break
        if not bulunan_sektor: return None, None
        
        toplam_fk = 0
        gecerli_rakip_sayisi = 0
        for rakip in sektorler[bulunan_sektor]:
            try:
                rakip_fk = yf.Ticker(rakip).info.get('trailingPE', 0)
                if rakip_fk and 0 < rakip_fk < 100:
                    toplam_fk += rakip_fk
                    gecerli_rakip_sayisi += 1
            except: pass
            
        if gecerli_rakip_sayisi > 0: return round(toplam_fk / gecerli_rakip_sayisi, 2), bulunan_sektor
        return None, bulunan_sektor

    # Grafik alanını önceden rezerve edip kilitliyoruz (Uçmayı engeller)
    grafik_alani = st.empty()

    df_all, info_data = get_full_data(hisse, zaman_sozlugu[secilen_int])

    if df_all.empty or 'Close' not in df_all.columns or len(df_all) < 5:
        st.error(f"⚠️ {hisse} anlık verisi yüklenirken gecikme yaşandı. Lütfen bekleyin, sistem otomatik tazeleyecektir.")
    else:
        df = df_all.copy()
        
        # Sütun tiplerini hatasız seriye indirgeme zırhı
        if hasattr(df['Close'], 'columns') or (type(df['Close']).__name__ == 'DataFrame'):
            df['Close'] = df['Close'].iloc[:, 0]
        if hasattr(df['Open'], 'columns') or (type(df['Open']).__name__ == 'DataFrame'):
            df['Open'] = df['Open'].iloc[:, 0]
        if hasattr(df['High'], 'columns') or (type(df['High']).__name__ == 'DataFrame'):
            df['High'] = df['High'].iloc[:, 0]
        if hasattr(df['Low'], 'columns') or (type(df['Low']).__name__ == 'DataFrame'):
            df['Low'] = df['Low'].iloc[:, 0]

        df['EMA7'] = df['Close'].ewm(span=7, adjust=False).mean()
        df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
        df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['EMA100'] = df['Close'].ewm(span=100, adjust=False).mean()
        df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
        
        delta = df['Close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=13, adjust=False).mean()
        avg_loss = loss.ewm(com=13, adjust=False).mean()
        df['RSI'] = 100 - (100 / (1 + (avg_gain / avg_loss)))
        
        ema12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD_12_26_9'] = ema12 - ema26
        df['MACDs_12_26_9'] = df['MACD_12_26_9'].ewm(span=9, adjust=False).mean()
        df['MACDh_12_26_9'] = df['MACD_12_26_9'] - df['MACDs_12_26_9']
        
        if view_period == "1 Ay": df_plot = df.tail(30).copy()
        elif view_period == "3 Ay": df_plot = df.tail(90).copy()
        elif view_period == "6 Ay": df_plot = df.tail(180).copy()
        elif view_period == "1 Yıl": df_plot = df.tail(365).copy()
        else: df_plot = df.copy()

        son_fiyat = float(df['Close'].iloc[-1])
        rsi_val = float(df['RSI'].iloc[-1])

        try:
            bugun = df_all.index[-1].date()
            gun_verisi = df_all[df_all.index.date == bugun]
            gun_acilisi = float(gun_verisi['Open'].iloc[0])
            onceki_gunler = df_all[df_all.index.date < bugun]
            if not onceki_gunler.empty:
                onceki_kapanis = float(onceki_gunler['Close'].iloc[-1])
                gunluk_yuzde = ((son_fiyat - onceki_kapanis) / onceki_kapanis) * 100
                delta_str = f"{gunluk_yuzde:.2f}%"
            else: delta_str = None
        except:
            gun_acilisi = float(df_all['Open'].iloc[-1])
            delta_str = None

        max_price = float(df_plot['High'].max())
        min_price = float(df_plot['Low'].min())
        fark = max_price - min_price
        fib_seviyeleri = {
            "0.0%": max_price, "23.6%": max_price - 0.236 * fark, "38.2%": max_price - 0.382 * fark,
            "50.0%": max_price - 0.5 * fark, "61.8%": max_price - 0.618 * fark, "78.6%": max_price - 0.786 * fark, "100.0%": min_price
        }

        x = np.arange(len(df_plot))
        y = df_plot['Close'].values
        
        if len(x) > 1:
            slope, intercept = np.polyfit(x, y, 1)
            df_plot['Orta_Trend'] = slope * x + intercept
            sapma = np.std(y - df_plot['Orta_Trend'])
            df_plot['Ust_Trend'] = df_plot['Orta_Trend'] + (sapma * 2)
            df_plot['Alt_Trend'] = df_plot['Orta_Trend'] - (sapma * 2)
            son_ust = float(df_plot['Ust_Trend'].iloc[-1])
            son_alt = float(df_plot['Alt_Trend'].iloc[-1])
        else:
            df_plot['Orta_Trend'] = df_plot['Close']
            df_plot['Ust_Trend'] = df_plot['Close']
            df_plot['Alt_Trend'] = df_plot['Close']
            son_ust, son_alt, slope = son_fiyat, son_fiyat, 0

        if son_fiyat > son_ust:
            kanal_durumu = f"🚀 DİKKAT: Kanalı YUKARI Kırdı! ({son_ust:.2f} Direnci Aşıldı - Aşırı Alım)"
            kanal_renk = "green"
        elif son_fiyat < son_alt:
            kanal_durumu = f"💥 DİKKAT: Kanalı AŞAĞI Kırdı! ({son_alt:.2f} Desteği Çöktü - Aşırı Satım)"
            kanal_renk = "red"
        elif slope > 0:
            kanal_durumu = f"📈 HİSSE YÜKSELEN TREND KANALINDA İLERLİYOR (Pozitif)"
            kanal_renk = "green"
        else:
            kanal_durumu = f"📉 HİSSE DÜŞEN TREND KANALINDA İLERLİYOR (Negatif)"
            kanal_renk = "orange"

        # Grafiği hafızada inşa ediyoruz
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name="Fiyat", increasing_line_color='#00C853', increasing_fillcolor='#00C853', decreasing_line_color='#D50000', decreasing_fillcolor='#D50000'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['Ust_Trend'], name="Kanal Üst", line=dict(color='rgba(255, 152, 0, 0.8)', width=2, dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['Alt_Trend'], name="Kanal Alt", line=dict(color='rgba(255, 152, 0, 0.8)', width=2, dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['Orta_Trend'], name="Trend Ekseni", line=dict(color='#000000', width=2.5, dash='dashdot')), row=1, col=1)

        for isim, deger in fib_seviyeleri.items():
            fig.add_hline(y=deger, line_dash="dot", line_color="gray", opacity=0.5, row=1, col=1)
            fig.add_annotation(x=df_plot.index[-1], y=deger, text=f"{isim}", showarrow=False, xanchor="left", xshift=5, font=dict(size=10, color="#555"), row=1, col=1)
        
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA21'], name="EMA 21 (Trend)", line=dict(color='#1f77b4', width=2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA50'], name="EMA 50 (Orta Vade)", line=dict(color='#FF9800', width=1.5, dash='dash')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA100'], name="EMA 100 (Ana Yön)", line=dict(color='#9C27B0', width=2, dash='dot')), row=1, col=1)
        
        if 'MACDh_12_26_9' in df_plot.columns:
            colors = ['#00C853' if val >= 0 else '#D50000' for val in df_plot['MACDh_12_26_9']]
            fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['MACDh_12_26_9'], name="MACD", marker_color=colors), row=2, col=1)
        
        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])], showspikes=True, spikemode="across", spikedash="dot")
        fig.update_layout(height=650, template="plotly_white", xaxis_rangeslider_visible=False, margin=dict(l=10, r=60, t=10, b=10), hovermode="x unified")
        
        # Rezerve ettiğimiz boşluğa grafiği basıyoruz
        grafik_alani.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

        if kanal_renk == "green": st.success(kanal_durumu)
        elif kanal_renk == "red": st.error(kanal_durumu)
        else: st.warning(kanal_durumu)

        st.markdown("### 📊 KRİTİK TEKNİK SEVİYELER")
        m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
        m1.metric("FİYAT", f"{son_fiyat:.2f}", delta_str)
        m2.metric("AÇILIŞ", f"{gun_acilisi:.2f}")
        m3.metric("FİBO %61.8", f"{fib_seviyeleri['61.8%']:.2f}")
        m4.metric("EMA 50", f"{df['EMA50'].iloc[-1]:.2f}")
        m5.metric("EMA 100", f"{df['EMA100'].iloc[-1]:.2f}")
        m6.metric("RSI", f"{rsi_val:.2f}")
        m7.metric("KANAL ÜSTÜ", f"{son_ust:.2f}")

        fk_val = info_data.get('trailingPE', 'N/A')
        pddd_val = info_data.get('priceToBook', 'N/A')
        favok_marji = info_data.get('ebitdaMargins', None)
        roe_val = info_data.get('returnOnEquity', None)
        oto_sektor_fk, sektor_adi = otonom_sektor_hesapla(hisse)

        st.markdown("### 🏢 ŞİRKET MALİ RÖNTGENİ")
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("F/K", f"{fk_val:.2f}" if isinstance(fk_val, float) else "N/A")
        k2.metric("PD/DD", f"{pddd_val:.2f}" if isinstance(pddd_val, float) else "N/A")
        k3.metric("FD/FAVÖK", f"{info_data.get('enterpriseToEbitda', 'N/A')}")
        k4.metric("FAVÖK Marjı", f"%{round(favok_marji*100, 2)}" if favok_marji else "N/A")
        
        if roe_val:
            roe_yuzde = roe_val * 100
            roe_str = f"%{roe_yuzde:.2f}"
            if roe_yuzde > 30: k5.success(f"**ROE:** {roe_str} (Mükemmel)")
            elif roe_yuzde > 15: k5.info(f"**ROE:** {roe_str} (İyi)")
            else: k5.error(f"**ROE:** {roe_str} (Düşük)")
        else: k5.metric("ROE", "N/A")

        if oto_sektor_fk and isinstance(fk_val, float):
            if fk_val < oto_sektor_fk: st.success(f"✅ **UCUZ:** Hissenin F/K'sı ({fk_val:.2f}), {sektor_adi} sektör ortalamasının ({oto_sektor_fk}) altında.")
            else: st.warning(f"⚠️ **PAHALI:** Hissenin F/K'sı ({fk_val:.2f}), {sektor_adi} sektör ortalamasının ({oto_sektor_fk}) üzerinde.")
        
        ai_puan = 0.0
        ai_rapor_maddeleri = []

        if isinstance(fk_val, float) and fk_val > 0:
            if oto_sektor_fk and fk_val < oto_sektor_fk:
                ai_puan += 1.5
                ai_rapor_maddeleri.append(f"📊 **F/K Oranı Olumlu:** Hisse F/K'sı ({fk_val:.2f}), rakip {sektor_adi} sektör ortalamasından ({oto_sektor_fk}) daha iskontolu.")
            elif fk_val < 15:
                ai_puan += 1.0
                ai_rapor_maddeleri.append(f"📊 **F/K Oranı Makul:** Sektör verisi eksik fakat {fk_val:.2f} genel piyasa çarpanlarına göre makul.")
            else:
                ai_rapor_maddeleri.append(f"🔺 **F/K Oranı Yüksek:** Hisse çarpanı ({fk_val:.2f}) yüksek.")

        if isinstance(pddd_val, float):
            if 0 < pddd_val < 3.5:
                ai_puan += 1.0
                ai_rapor_maddeleri.append(f"📑 **Defter Değeri Dengeli:** PD/DD oranı {pddd_val:.2f} ile güvenli bölgede.")
            else:
                ai_rapor_maddeleri.append(f"🔺 **Yüksek PD/DD:** Özsermayesinin {pddd_val:.2f} katından işlem görüyor.")

        if roe_val:
            if roe_val > 0.30:
                ai_puan += 1.5
                ai_rapor_maddeleri.append(f"💰 **Mükemmel Özsermaye Kârlılığı (ROE):** %{roe_val*100:.2f} ile parasını verimli büyütüyor.")
            elif roe_val > 0.15:
                ai_puan += 1.0
                ai_rapor_maddeleri.append(f"💰 **Yeterli Kârlılık (ROE):** %{roe_val*100:.2f} rasyosu makul.")

        if favok_marji and favok_marji > 0.15:
            ai_puan += 1.0
            ai_rapor_maddeleri.append(f"🏭 **Güçlü Operasyonel Kâr:** FAVÖK marjı %{favok_marji*100:.2f} ile güçlü nakit üretiyor.")

        if 30 <= rsi_val <= 45:
            ai_puan += 2.0
            ai_rapor_maddeleri.append(f"🎯 **RSI Toplama Bölgesinde:** RSI {rsi_val:.2f} seviyesinde; dönüş için ideal güç toplama alanında.")
        elif 45 < rsi_val <= 60:
            ai_puan += 1.0
            ai_rapor_maddeleri.append(f"📊 **RSI Dengeli:** RSI {rsi_val:.2f} ile nötr bölgede.")
        elif rsi_val < 30:
            ai_puan += 1.5
            ai_rapor_maddeleri.append(f"🔥 **Aşırı Satım Bölgesi:** RSI {rsi_val:.2f} ile aşırı düştü, teknik tepki gelebilir.")
        else:
            ai_rapor_maddeleri.append(f"⚠️ **RSI Şişkinlik Sinyali:** RSI {rsi_val:.2f} ile aşırı alıma yakın.")

        if son_fiyat > df['EMA50'].iloc[-1]:
            ai_puan += 1.0
            ai_rapor_maddeleri.append("📈 **EMA Trend Gücü Üstün:** Fiyat 50 günlük hareketli ortalamanın üzerinde.")
        else:
            ai_rapor_maddeleri.append("📉 **EMA Trend Baskısı:** Orta vadeli EMA50 ortalamasının altında.")

        if slope > 0:
            ai_puan += 1.0
            ai_rapor_maddeleri.append("📐 **Kanal Eğimi Pozitif:** Lineer regresyon kanal yönü yukarı eğimli.")

        fibo_618 = fib_seviyeleri['61.8%']
        ema_100 = df['EMA100'].iloc[-1]
        
        if fibo_618 != 0 and abs((son_fiyat - fibo_618) / fibo_618) <= 0.05:
            ai_puan += 1.0
            ai_rapor_maddeleri.append("🛡️ **Kritik Kaya Destek Yakınlığı:** Fiyat, güçlü Fibonacci %61.8 kalesine çok yakın.")
        elif ema_100 != 0 and abs((son_fiyat - ema_100) / ema_100) <= 0.05:
            ai_puan += 1.0
            ai_rapor_maddeleri.append("🛡️ **Kritik Kaya Destek Yakınlığı:** Fiyat, güçlü EMA 100 kalesine çok yakın.")

        ai_puan = min(10.0, max(0.0, round(ai_puan, 1)))
        doluluk_yuzdesi = int((ai_puan / 10.0) * 100)
        anlik_zaman = time.time()

        if ai_puan >= 6.0 and st.session_state[state_sinyal_key] == "NÖTR (İZLE)":
            if (anlik_zaman - st.session_state[state_zaman_key]) > 50.0:
                st.session_state[state_sinyal_key] = "ALINABİLİR / GÜÇLÜ"
                st.session_state[state_fiyat_key] = son_fiyat
                st.session_state[state_zaman_key] = anlik_zaman
                
                gerekce_metni = "\n".join([madde for madde in ai_rapor_maddeleri if any(x in madde for x in ["Olumlu", "Makul", "Bölgesinde", "Üstün", "Pozitif", "Yakınlığı"])])
                mesaj_metni = (
                    f"🇹🇷 🤖 *BIST HİBRİT MOTOR ALARMI*\n\n"
                    f"**Hisse:** #{hisse.replace('.IS', '')}\n"
                    f"**Anlık Fiyat:** `{son_fiyat:.2f} TL`\n"
                    f"**Yapay Zeka Skoru:** `{ai_puan} / 10` 🎯\n\n"
                    f"**🔍 Tetiklenme Gerekçeleri:**\n{gerekce_metni}"
                )
                telegram_bist_sinyal_gonder(mesaj_metni)
                time.sleep(0.5)
        elif ai_puan < 4.5:
            st.session_state[state_sinyal_key] = "NÖTR (İZLE)"
            st.session_state[state_fiyat_key] = 0.0

        st.markdown("<div class='ai-score-box'>", unsafe_allow_html=True)
        st.markdown(f"<h2>🤖 YAPAY ZEKA HİBRİT KARAR MOTORU (ÖZET RAPOR)</h2>", unsafe_allow_html=True)
        st.markdown(f"<h1>{ai_puan} <span style='font-size: 1.5rem; color: #aaa;'>/ 10</span></h1>", unsafe_allow_html=True)
        
        # Maddeleri ekrana yazdırma alanı
        for m in ai_rapor_maddeleri:
            st.markdown(f"<p style='margin: 5px 0; font-size: 1rem;'>{m}</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
