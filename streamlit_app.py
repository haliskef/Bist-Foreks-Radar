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
st.set_page_config(page_title="BIST & KÜRESEL HİBRİT KOMUTA MERKEZİ",
    layout="wide",                       # Geniş ekran modu
    initial_sidebar_state="collapsed"    # Telefonda sidebar gizli başlar!
)
# UI/UX OPTİMİZASYONU
st.markdown("""
    <style>
    .main, .stApp { background-color: #FDFCF0 !important; }
    section[data-testid="stSidebar"] { background-color: #F0EDE0 !important; border-right: 1px solid #D1D1D1; }
    p, span, label, .stMarkdown { color: #000000 !important; font-weight: 700 !important; font-size: 1.1rem !important; }
    h1, h2, h3 { color: #1A1A1A !important; font-weight: 900 !important; border-bottom: 2px solid #1A1A1A !important; padding-bottom: 10px; }
    
    .stMetric { background-color: #FFFFFF !important; padding: 10px 5px !important; border-radius: 10px !important; border: 1px solid #CCCCCC !important; box-shadow: 2px 2px 5px rgba(0,0,0,0.05) !important; }
    
    [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] > div { 
        color: #555555 !important; font-weight: 800 !important; white-space: normal !important; 
        word-wrap: break-word !important; overflow: visible !important; text-overflow: clip !important; 
        font-size: 0.75rem !important; line-height: 1.2 !important;
    }
    
    [data-testid="stMetricValue"], [data-testid="stMetricValue"] > div { 
        color: #000000 !important; font-weight: 900 !important; font-size: 1.15rem !important; 
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
# =================================================================================
# =================================================================================
# ÇEKİRDEK 1: LAZER MODU (GRAFİK KAYBOLMA VE KİLİTLENME HATALARI GİDERİLMİŞ SÜRÜM)
# =================================================================================
if calisma_modu == "Lazer (Detaylı Analiz & Strateji)":
    # Tarayıcı kilitlenmesini önlemek için autorefresh mekanizmasını Lazer moduna özel optimize ettik
    st_autorefresh(interval=45000, limit=500, key="lazer_canli_guncelleme_fixed_v2")
    
    import time
    import threading
    import numpy as np
    import pandas as pd
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

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
                import requests
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
                    ticker_o = yf.Ticker(o_kod)
                    df_o = ticker_o.history(period="1mo", interval="1d")
                    if df_o.empty or len(df_o) < 5: continue
                    if isinstance(df_o.columns, pd.MultiIndex): df_o.columns = df_o.columns.get_level_values(0)
                    df_o.columns = [str(c).strip().capitalize() for c in df_o.columns]

                    df_o['EMA50'] = df_o['Close'].ewm(span=50, adjust=False).mean()
                    delta_o = df_o['Close'].diff()
                    gain_o = delta_o.clip(lower=0)
                    loss_o = -delta_o.clip(upper=0)
                    rsi_o = 100 - (100 / (1 + (gain_o.ewm(com=13, adjust=False).mean() / loss_o.ewm(com=13, adjust=False).mean()))).iloc[-1].item()
                    
                    fiyat_o = df_o['Close'].iloc[-1].item()
                    info_o = ticker_o.info
                    fk_o = info_o.get('trailingPE', None)
                    pddd_o = info_o.get('priceToBook', None)
                    roe_o = info_o.get('returnOnEquity', None)
                    favok_o = info_o.get('ebitdaMargins', None)

                    o_puan = 0.0
                    o_maddeler = []

                    if isinstance(fk_o, float) and 0 < fk_o < 15: 
                        o_puan += 1.0; o_maddeler.append(f"📊 F/K Oranı Makul ({fk_o:.2f})")
                    if isinstance(pddd_o, float) and 0 < pddd_o < 3.5: 
                        o_puan += 1.0; o_maddeler.append(f"📑 Defter Değeri Dengeli ({pddd_o:.2f})")
                    if roe_o and roe_o > 0.30: 
                        o_puan += 1.5; o_maddeler.append(f"💰 Mükemmel Özsermaye Kârlılığı (%{roe_o*100:.1f})")
                    if favok_o and favok_o > 0.15: 
                        o_puan += 1.0; o_maddeler.append(f"🏭 Güçlü Operasyonel Kâr (%{favok_o*100:.1f})")
                    if 30 <= rsi_o <= 45: 
                        o_puan += 2.0; o_maddeler.append(f"🎯 RSI Toplama Bölgesinde ({rsi_o:.1f})")
                    elif rsi_o < 30: 
                        o_puan += 1.5; o_maddeler.append(f"🔥 Aşırı Satım Bölgesi ({rsi_o:.1f})")
                    if fiyat_o > df_o['EMA50'].iloc[-1]: 
                        o_puan += 1.0; o_maddeler.append("📈 EMA Trend Gücü Üstün")

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
        
    # Grafiği uçurmayan, her hisse değişiminde önbelleği tazeleyen esnek fonksiyon
    @st.cache_data(ttl=20, show_spinner=False)
    def get_full_data(kod, interval):
        for deneme in range(3):
            try:
                ticker = yf.Ticker(kod)
                p = "2y" if interval in ["1h", "1d"] else "1mo"
                data = ticker.history(period=p, interval=interval)
                if data.empty or len(data) < 5:
                    data = ticker.history(period="2y", interval="1d")
                    
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
                time.sleep(1.5)
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
        st.error(f"⚠️ {hisse} verisi yüklenirken gecikme yaşandı. Lütfen saniyeler sonra sayfayı manuel yenileyin veya başka koda geçin.")
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
        
        # Rezerve ettiğimiz boşluğa grafiği basıyoruz (Kaybolma ihtimalini sıfırlar)
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
                ai_puan += 1.5; ai_rapor_maddeleri.append(f"📊 **F/K Oranı Olumlu:** Hisse F/K'sı ({fk_val:.2f}), rakip {sektor_adi} sektör ortalamasından ({oto_sektor_fk}) daha iskontolu.")
            elif fk_val < 15: 
                ai_puan += 1.0; ai_rapor_maddeleri.append(f"📊 **F/K Oranı Makul:** Sektör verisi eksik fakat {fk_val:.2f} genel piyasa çarpanlarına göre makul.")
            else: ai_rapor_maddeleri.append(f"🔺 **F/K Oranı Yüksek:** Hisse çarpanı ({fk_val:.2f}) yüksek.")
        
        if isinstance(pddd_val, float):
            if 0 < pddd_val < 3.5: 
                ai_puan += 1.0; ai_rapor_maddeleri.append(f"📑 **Defter Değeri Dengeli:** PD/DD oranı {pddd_val:.2f} ile güvenli bölgede.")
            else: ai_rapor_maddeleri.append(f"🔺 **Yüksek PD/DD:** Özsermayesinin {pddd_val:.2f} katından işlem görüyor.")

        if roe_val:
            if roe_val > 0.30: 
                ai_puan += 1.5; ai_rapor_maddeleri.append(f"💰 **Mükemmel Özsermaye Kârlılığı (ROE):** %{roe_val*100:.2f} ile parasını verimli büyütüyor.")
            elif roe_val > 0.15: 
                ai_puan += 1.0; ai_rapor_maddeleri.append(f"💰 **Yeterli Kârlılık (ROE):** %{roe_val*100:.2f} rasyosu makul.")
        
        if favok_marji and favok_marji > 0.15: 
            ai_puan += 1.0; ai_rapor_maddeleri.append(f"🏭 **Güçlü Operasyonel Kâr:** FAVÖK marjı %{favok_marji*100:.2f} ile güçlü nakit üretiyor.")

        if 30 <= rsi_val <= 45: 
            ai_puan += 2.0; ai_rapor_maddeleri.append(f"🎯 **RSI Toplama Bölgesinde:** RSI {rsi_val:.2f} seviyesinde; dönüş için ideal güç toplama alanında.")
        elif 45 < rsi_val <= 60: 
            ai_puan += 1.0; ai_rapor_maddeleri.append(f"📊 **RSI Dengeli:** RSI {rsi_val:.2f} ile nötr bölgede.")
        elif rsi_val < 30: 
            ai_puan += 1.5; ai_rapor_maddeleri.append(f"🔥 **Aşırı Satım Bölgesi:** RSI {rsi_val:.2f} ile aşırı düştü, teknik tepki gelebilir.")
        else: ai_rapor_maddeleri.append(f"⚠️ **RSI Şişkinlik Sinyali:** RSI {rsi_val:.2f} ile aşırı alıma yakın.")

        if son_fiyat > df['EMA50'].iloc[-1]: 
            ai_puan += 1.0; ai_rapor_maddeleri.append("📈 **EMA Trend Gücü Üstün:** Fiyat 50 günlük hareketli ortalamanın üzerinde.")
        else: ai_rapor_maddeleri.append("📉 **EMA Trend Baskısı:** Orta vadeli EMA50 ortalamasının altında.")
            
        if slope > 0: 
            ai_puan += 1.0; ai_rapor_maddeleri.append("📐 **Kanal Eğimi Pozitif:** Lineer regresyon kanal yönü yukarı eğimli.")

        fibo_618 = fib_seviyeleri['61.8%']
        ema_100 = df['EMA100'].iloc[-1]
        if fibo_618 != 0 and abs((son_fiyat - fibo_618) / fibo_618) <= 0.05:
            ai_puan += 1.0; ai_rapor_maddeleri.append("🛡️ **Kritik Kaya Destek Yakınlığı:** Fiyat, güçlü Fibonacci %61.8 kalesine çok yakın.")
        elif ema_100 != 0 and abs((son_fiyat - ema_100) / ema_100) <= 0.05:
            ai_puan += 1.0; ai_rapor_maddeleri.append("🛡️ **Kritik Kaya Destek Yakınlığı:** Fiyat, güçlü EMA 100 kalesine çok yakın.")

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
        st.markdown(f"<h1>{ai_puan} <span style='font-size: 1.5rem; color: #AAAAAA;'>/ 10</span></h1>", unsafe_allow_html=True)
        st.markdown(f"""
        <div style="width: 100%; background-color: #111111; height: 14px; border-radius: 7px; margin-bottom: 20px;">
            <div style="width: {doluluk_yuzdesi}%; background: linear-gradient(90deg, #FF8C00 0%, #FFD700 100%); height: 100%; border-radius: 7px;"></div>
        </div>
        """, unsafe_allow_html=True)
        
        if rsi_val > 75 or son_fiyat >= son_ust: st.error("🚨 **SİSTEM UYARISI: KÂR ALMA / SATIŞ BÖLGESİ! Fiyat doygunluğa ulaştı.**")
        elif ai_puan >= 7.5: st.success("🟢 **KUSURSUZ FIRSAT (GÜÇLÜ ALIM): Temel rasyolar ucuz ve teknik destekler sağlam konumda.**")
        elif ai_puan >= 5.0: st.warning("🟡 **POTANSİYEL (İZLEME VE KADEMELİ ALIM): Belirli kriterler olumlu fakat teyit beklenmeli.**")
        else: st.error("🔴 **RİSKLİ BÖLGE (UZAK DUR): Çarpanlar pahalı veya teknik göstergeler aşağı yönlü kırılım aşamasında.**")
            
        st.markdown("#### 🔍 SİSTEM GEREKÇELERİ VE SINYAL DETAYLARI:")
        for madde in ai_rapor_maddeleri: st.markdown(f"<span style='color: #FFFFFF !important;'>{madde}</span>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("## 🌍 ANA PİYASA DURUMU (BIST 100 & 30)")
        
        @st.cache_data(ttl=60, show_spinner=False)
        def get_index_data(symbol):
            data = yf.download(symbol, period="6mo", interval="1d", progress=False)
            if data.empty: return pd.DataFrame()
            if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
            data.columns = [str(c).strip().capitalize() for c in data.columns]
            
            data['EMA21'] = data['Close'].ewm(span=21, adjust=False).mean()
            data['EMA50'] = data['Close'].ewm(span=50, adjust=False).mean()
            
            idx_delta = data['Close'].diff()
            idx_gain = idx_delta.clip(lower=0)
            idx_loss = -idx_delta.clip(upper=0)
            data['RSI'] = 100 - (100 / (1 + (idx_gain.ewm(com=13, adjust=False).mean() / idx_loss.ewm(com=13, adjust=False).mean())))
            return data

        def endeks_yorumla(df_idx):
            if df_idx.empty: return "Veri alınamadı.", "gray"
            son_kapanis = float(df_idx['Close'].iloc[-1])
            e21 = float(df_idx['EMA21'].iloc[-1])
            e50 = float(df_idx['EMA50'].iloc[-1])
            rsi_idx = float(df_idx['RSI'].iloc[-1])
            
            if son_kapanis > e21 and e21 > e50: trend = "🚀 GÜÇLÜ BOĞA PİYASASI: Endeks ana ortalamaların üzerinde, yükseliş trendi korunuyor." ; renk = "green"
            elif son_kapanis < e21 and e21 < e50: trend = "💥 AYI PİYASASI BASKISI: Fiyat ortalamaların altında, temkinli olunmalı." ; renk = "red"
            else: trend = "⏳ KONSOLİDASYON / KARARSIZ BÖLGE: Ortalamalar birbirine yakın, yatay seyir hakim." ; renk = "orange"
                
            if rsi_idx > 70: momentum = "⚠️ AŞIRI ALIM: RSI 70 üzerinde. Kısa vadeli kâr satışlarına dikkat edilmeli."
            elif rsi_idx < 30: momentum = "🔥 AŞIRI SATIM: RSI 30 altında. Tepki alımları gelebilir."
            else: momentum = f"📊 MOMENTUM DENGELİ: RSI {rsi_idx:.2f} ile dengeli / sağlıklı bölgede."
            return f"**Trend:** {trend}\n\n**Momentum:** {momentum}", renk

        idx_col1, idx_col2 = st.columns(2)
        with idx_col1:
            st.subheader("BIST 100 (XU100)")
            df_x100 = get_index_data("XU100.IS")
            if not df_x100.empty:
                son_100 = float(df_x100['Close'].iloc[-1])
                onceki_100 = float(df_x100['Close'].iloc[-2])
                degisim_100 = ((son_100 - onceki_100) / onceki_100) * 100
                st.metric("Puan", f"{son_100:.2f}", f"{degisim_100:.2f}%")
                
                fig100 = go.Figure(go.Scatter(x=df_x100.index[-60:], y=df_x100['Close'].tail(60), line=dict(color='#1f77b4', width=3)))
                fig100.update_layout(height=100, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_visible=False, yaxis_visible=False)
                st.plotly_chart(fig100, use_container_width=True)
                
                yorum_100, renk_100 = endeks_yorumla(df_x100)
                if renk_100 == "green": st.success(yorum_100)
                elif renk_100 == "red": st.error(yorum_100)
                else: st.warning(yorum_100)

        with idx_col2:
            st.subheader("BIST 30 (XU030)")
            df_x030 = get_index_data("XU030.IS")
            if not df_x030.empty:
                son_30 = float(df_x030['Close'].iloc[-1])
                onceki_30 = float(df_x030['Close'].iloc[-2])
                degisim_30 = ((son_30 - onceki_30) / onceki_30) * 100
                st.metric("Puan", f"{son_30:.2f}", f"{degisim_30:.2f}%")
                
                fig30 = go.Figure(go.Scatter(x=df_x030.index[-60:], y=df_x030['Close'].tail(60), line=dict(color='#9C27B0', width=3)))
                fig30.update_layout(height=100, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_visible=False, yaxis_visible=False)
                st.plotly_chart(fig30, use_container_width=True)
                
                yorum_30, renk_30 = endeks_yorumla(df_x030)
                if renk_30 == "green": st.success(yorum_30)
                elif renk_30 == "red": st.error(yorum_30)
                else: st.warning(yorum_30)

        st.markdown("---")
        st.markdown("## 🤖 AKTİF POZİSYON TAKİP VE ALARM MERKEZİ")
        if 'secili_hisse' not in st.session_state or st.session_state.secili_hisse != hisse:
            st.session_state.secili_hisse = hisse
            st.session_state.kullanici_maliyeti = float(son_fiyat)
        maliyet = st.number_input("Hisse Alım Maliyetiniz (TL):", value=float(st.session_state.kullanici_maliyeti), step=0.01, format="%.2f")
        st.session_state.kullanici_maliyeti = maliyet 
        h_kar, z_kes = st.columns(2)
        with h_kar: hedef_kar = st.slider("Hedef Kâr Yüzdesi (%):", 1, 100, 15)
        with z_kes: zarar_kes = st.slider("Zarar Kes (Stop Loss) Yüzdesi (%):", 1, 25, 5)
        hedef_fiyat = maliyet * (1 + hedef_kar/100)
        stop_fiyat = maliyet * (1 - zarar_kes/100)
        anlik_durum_yuzde = ((son_fiyat - maliyet) / maliyet) * 100
        c1, c2, c3 = st.columns(3)
        c1.info(f"🎯 HEDEF FİYAT:\n### {hedef_fiyat:.2f} TL")
        if anlik_durum_yuzde > 0: c2.success(f"📈 ANLIK DURUM:\n### +%{anlik_durum_yuzde:.2f}")
        else: c2.error(f"📉 ANLIK DURUM:\n### %{anlik_durum_yuzde:.2f}")
        c3.error(f"🛑 STOP FİYATI:\n### {stop_fiyat:.2f} TL")
# =================================================================================
# =================================================================================
# =================================================================================
# ÇEKİRDEK 2: FULL HİBRİT RADAR (HATASIZ VE SAF PANDAS HESAPLAMALI YENİ SÜRÜM)
# =================================================================================
elif calisma_modu == "Radar (BIST 100 Full Hibrit Tarama)":
    st.markdown("## 📡 BIST 100 DERİN HİBRİT TARAMA (TEKNİK + TEMEL)")
    if 'hibrit_tablo_full' not in st.session_state:
        try: st.session_state.hibrit_tablo_full = pd.read_csv("son_tarama_kaydi.csv")
        except FileNotFoundError: st.session_state.hibrit_tablo_full = pd.DataFrame()

    bist100_tam_liste = [
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

    if st.button("🚀 FULL DERİN TARAMAYI BAŞLAT", use_container_width=True):
        ilerleme = st.progress(0)
        durum_m = st.empty()
        sonuclar = []
        
        for i, kod in enumerate(bist100_tam_liste):
            durum_m.text(f"⏳ Analiz Ediliyor: {kod} ({i+1}/{len(bist100_tam_liste)})")
            try:
                t = yf.Ticker(kod)
                hist = t.history(period="6mo", interval="1d")
                
                # Sütun yapısı düzleştirme koruması
                if isinstance(hist.columns, pd.MultiIndex):
                    hist.columns = hist.columns.get_level_values(0)
                hist.columns = [str(c).strip().capitalize() for c in hist.columns]
                
                if hist.empty or len(hist) < 22: 
                    continue
                
                # Güvenli tekil seriye indirgeme (hata vermez kalıp)
                if hasattr(hist['Close'], 'columns') or (type(hist['Close']).__name__ == 'DataFrame'): hist['Close'] = hist['Close'].iloc[:, 0]
                
                skor = 0
                son_fiyat = float(hist['Close'].iloc[-1])
                
                # 🛠️ NATIVE EMA21 HESAPLAMASI (Kütüphane bağımlılığı olmadan)
                hist['EMA21'] = hist['Close'].ewm(span=21, adjust=False).mean()
                ema21_val = float(hist['EMA21'].iloc[-1])
                
                # 🛠️ NATIVE RSI14 HESAPLAMASI (Kütüphane bağımlılığı olmadan)
                delta = hist['Close'].diff()
                gain = delta.clip(lower=0)
                loss = -delta.clip(upper=0)
                avg_gain = gain.ewm(com=13, adjust=False).mean()
                avg_loss = loss.ewm(com=13, adjust=False).mean()
                rs = avg_gain / avg_loss
                hist['RSI'] = 100 - (100 / (1 + rs))
                rsi_val = float(hist['RSI'].iloc[-1])
                
                # Temel Verileri Güvenli Çekme Katmanı
                inf = t.info
                fk = inf.get('trailingPE', 100)
                pddd = inf.get('priceToBook', 100)
                roe = inf.get('returnOnEquity', 0)
                
                # Skorlama Motoru Kontrolleri
                if son_fiyat > ema21_val: skor += 1
                if 30 < rsi_val < 65: skor += 1
                if fk is not None and fk < 15: skor += 1
                if pddd is not None and pddd < 3: skor += 1
                if roe is not None and roe > 0.20: skor += 1

                sonuclar.append({
                    "Hisse": kod.replace(".IS", ""), 
                    "Fiyat": round(son_fiyat, 2),
                    "F/K": round(fk, 2) if (fk is not None and fk != 100) else "N/A", 
                    "PD/DD": round(pddd, 2) if (pddd is not None and pddd != 100) else "N/A",
                    "ROE (%)": round(roe * 100, 2) if roe else "N/A", 
                    "RSI": round(rsi_val, 2), 
                    "Hibrit Skor": skor,
                    "Sistem Notu": "👑 ŞAMPİYON" if skor >= 4 else ("🟢 GÜÇLÜ" if skor == 3 else ("🟡 MAKUL" if skor == 2 else "⚪ İZLE"))
                })
                time.sleep(0.05)
            except Exception as e: 
                pass # Hata veren hisseyi atla, döngüyü bozma
                
            ilerleme.progress((i + 1) / len(bist100_tam_liste))
            
        if sonuclar:
            df_sonuc = pd.DataFrame(sonuclar).sort_values(by="Hibrit Skor", ascending=False).reset_index(drop=True)
            st.session_state.hibrit_tablo_full = df_sonuc
            df_sonuc.to_csv("son_tarama_kaydi.csv", index=False)
            durum_m.success("✅ Tüm BIST 100 Başarıyla Taranıp Kaydedildi!")
        else:
            durum_m.error("❌ Tarama sırasında veri çekilemedi.")

    # Tabloyu Ekrana Basma Bölümü
    if not st.session_state.hibrit_tablo_full.empty:
        def renk_motoru(val):
            if val == "👑 ŞAMPİYON": return 'background-color: #FFD700; color: black; font-weight: bold;'
            if val == "🟢 GÜÇLÜ": return 'background-color: #C8E6C9; color: black; font-weight: bold;'
            return ''
        styled_df = st.session_state.hibrit_tablo_full.style.map(renk_motoru, subset=['Sistem Notu'])
        st.dataframe(styled_df, use_container_width=True, height=800)

# =================================================================================
# =================================================================================
# ÇEKİRDEK 3: FOREX & KÜRESEL PİYASALAR (TAM OTONOM ÇOKLU ENSTRÜMAN RADARI - ASIL SABİT DESTEK/DİRENÇLİ)
# =================================================================================
elif calisma_modu == "Forex & Küresel Piyasalar (Çift Yönlü)":
    st_autorefresh(interval=60000, key="global_forex_multi_scan_v15_final_sabit_kaleler")
    st.markdown("## 🌐 ÇİFT YÖNLÜ OTONOM FOREX KOMUTA MERKEZİ (TÜM LİSTE ARKA PLANDA TARANIYOR)")
    
    # -----------------------------------------------------------------------------
    # TELEGRAM ENTEGRASYON BÖLÜMÜ
    # -----------------------------------------------------------------------------
    TELEGRAM_BOT_TOKEN = "8817119197:AAHcHADLXZ7DbLgJp7yskg94QO0Q6jJd85s"
    TELEGRAM_CHAT_ID = "1338802399"

    def telegram_sinyal_gonder(mesaj):
        """Kırılım anında Telegram üzerinden anlık bildirim atar."""
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            try:
                import requests
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mesaj, "parse_mode": "Markdown"}
                requests.post(url, json=payload, timeout=5)
            except Exception as e:
                pass 

    # SEKMELİ YAPI (Grafik Paneli ve Geniş Haber Paneli Ayrımı)
    fx_tab1, fx_tab2 = st.tabs(["📊 Otonom Teknik Analiz & PA", "📅 Canlı Ekonomik Takvim & Makro Etki"])
    
    with fx_tab2:
        st.markdown("### 📰 Küresel Makroekonomik Takvim (Maksimum Genişlik & Türkçe)")
        st.warning("⚠️ **Volatilite Uyarısı:** Yüksek etkili (3 Yıldızlı / Kırmızı) verilerin açıklanma saatlerinde teknik indikatörler devredışı kalabilir. Haber saatinden 15 dk önce ve sonra işlem riskini minimuma indirin.")
        
        ekonomik_takvim_html = """
        <div style="position: relative; width: 100%; margin: 0; padding: 0;">
            <style>
                html, body { margin: 0; padding: 0; overflow-x: hidden; }
                .tradingview-widget-container { width: 100% !important; height: 900px !important; }
            </style>
            <div class="tradingview-widget-container">
              <div class="tradingview-widget-container__widget" style="width: 100%; height: 100%;"></div>
              <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
              {
              "colorTheme": "light",
              "isWidescreen": true,
              "width": "100%",
              "height": "100%",
              "locale": "tr",
              "importanceFilter": "-1,0,1",
              "countryFilter": "us,eu,gb,jp,ch,ca,au,tr"
              }
              </script>
            </div>
        </div>
        """
        st.components.v1.html(ekonomik_takvim_html, height=950, scrolling=True)
        
    with fx_tab1:
        # Sabit Test Butonu
        if st.button("🚀 Sistem Bildirim Testini Tetikle"):
            try:
                import requests
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                payload = {"chat_id": TELEGRAM_CHAT_ID, "text": "🎯 *SİSTEM TESTİ BAŞARILI!*\n\nAsıl Sabit Kaleli çoklu tarama modunda Telegram hattınız aktiftir.", "parse_mode": "Markdown"}
                response = requests.post(url, json=payload, timeout=5)
                if response.status_code == 200: st.success("🎯 Harika! Mesaj başarıyla gönderildi. Telefonunu kontrol et.")
                else: st.error(f"❌ Telegram API Hata Döndürdü: {response.text}")
            except Exception as e: st.error(f"🚨 Sunucu/Ağ Bağlantı Hatası: {e}")

        st.info("🔄 **7/24 Arka Plan Tarayıcısı Aktif:** Grafik üzerinde kalın düz çizgiler ASIL SABİT kaleleri, kesikli ince çizgiler ise yürüyen anlık momentum seviyelerini gösterir.")
        
        # Ekranda detaylarını, nedenlerini ve grafiğini görmek istediğin enstrüman seçimi
        secilen_forex_adi = st.selectbox("Ekranda Detaylı İncelemek İstediğiniz Küresel Enstrüman:", list(forex_assets.keys()))
        
        # Sırlama hatasını engellemek için listeyi en başta boş küme olarak sağlama alıyoruz
        sonuclar = []

        # 🤖 OTONOM ÇOKLU TARAMA DÖNGÜSÜ
        for asset_adi, asset_ticker in forex_assets.items():
            
            # Her enstrüman için bağımsız hafıza alanı kilitliyoruz
            state_sinyal_key = f"fx_state_yon_{asset_adi}"
            state_fiyat_key = f"fx_lock_price_{asset_adi}"
            
            if state_sinyal_key not in st.session_state: st.session_state[state_sinyal_key] = "NÖTR (İZLE)"
            if state_fiyat_key not in st.session_state: st.session_state[state_fiyat_key] = 0.0
            
            try:
                df_fx = yf.download(tickers=asset_ticker, period="1mo", interval="1h", progress=False)
            except:
                continue
                
            if not df_fx.empty and len(df_fx) > 25:
                # --- ÇOK KATMANLI VERİ YAPISINI (USA/FOREX) KESİN DÜZLEŞTİRME KORUMASI ---
                if isinstance(df_fx.columns, pd.MultiIndex): 
                    df_fx.columns = df_fx.columns.get_level_values(0)
                df_fx.columns = [str(c).strip().capitalize() for c in df_fx.columns]
                
                # Sütunların DataFrame mi yoksa Series mi olduğunu hatasız çözen yeni zırh katmanı
                if hasattr(df_fx['Open'], 'columns') or (type(df_fx['Open']).__name__ == 'DataFrame'): df_fx['Open'] = df_fx['Open'].iloc[:, 0]
                if hasattr(df_fx['High'], 'columns') or (type(df_fx['High']).__name__ == 'DataFrame'): df_fx['High'] = df_fx['High'].iloc[:, 0]
                if hasattr(df_fx['Low'], 'columns') or (type(df_fx['Low']).__name__ == 'DataFrame'): df_fx['Low'] = df_fx['Low'].iloc[:, 0]
                if hasattr(df_fx['Close'], 'columns') or (type(df_fx['Close']).__name__ == 'DataFrame'): df_fx['Close'] = df_fx['Close'].iloc[:, 0]
                
                # 🏃 1. DİNAMİK/YÜRÜYEN SEVİYELER (Momentum Takibi - Son 15 Mum)
                df_fx['Direnç_S1'] = df_fx['High'].rolling(window=15).max().shift(1)
                df_fx['Destek_D1'] = df_fx['Low'].rolling(window=15).min().shift(1)
                
                # 🏛️ 2. ASIL SABİT PSİKOLOJİK KALELER (Geniş Zamanlı Klasik Pivot Kümesi)
                gecmis_high = df_fx['High'].tail(24).max()
                gecmis_low = df_fx['Low'].tail(24).min()
                gecmis_close = df_fx['Close'].tail(24).mean() # Gürültüyü engellemek için ortalama denge noktası
                
                sabit_pivot = (gecmis_high + gecmis_low + gecmis_close) / 3
                asıl_direnc_kale = (2 * sabit_pivot) - gecmis_low
                asıl_destek_kale = (2 * sabit_pivot) - gecmis_high
                
                # 3. Kristal Box Hesaplamaları (Donchian)
                df_fx['box_ust'] = df_fx['High'].rolling(window=20).max()
                df_fx['box_alt'] = df_fx['Low'].rolling(window=20).min()
                df_fx['box_orta'] = (df_fx['box_ust'] + df_fx['box_alt']) / 2
                
                # 4. Native ATR & Teknik İndikatör Hesaplamaları
                high_low = df_fx['High'] - df_fx['Low']
                high_close = (df_fx['High'] - df_fx['Close'].shift()).abs()
                low_close = (df_fx['Low'] - df_fx['Close'].shift()).abs()
                ranges = pd.concat([high_low, high_close, low_close], axis=1)
                true_range = ranges.max(axis=1)
                df_fx['ATR'] = true_range.ewm(alpha=1/14, adjust=False).mean()
                
                fx_delta = df_fx['Close'].diff()
                fx_gain = fx_delta.clip(lower=0)
                fx_loss = -fx_delta.clip(upper=0)
                fx_avg_gain = fx_gain.ewm(com=13, adjust=False).mean()
                fx_avg_loss = fx_loss.ewm(com=13, adjust=False).mean()
                fx_rs = fx_avg_gain / fx_avg_loss
                df_fx['RSI'] = 100 - (100 / (1 + fx_rs))
                
                df_fx['EMA21'] = df_fx['Close'].ewm(span=21, adjust=False).mean()
                df_fx['EMA50'] = df_fx['Close'].ewm(span=50, adjust=False).mean()
                
                son_fiyat = float(df_fx['Close'].iloc[-1])
                atr_val = float(df_fx['ATR'].iloc[-1])
                rsi_val = float(df_fx['RSI'].iloc[-1])
                b_ust = float(df_fx['box_ust'].iloc[-2])
                b_alt = float(df_fx['box_alt'].iloc[-2])
                ema21 = float(df_fx['EMA21'].iloc[-1])
                ema50 = float(df_fx['EMA50'].iloc[-1])
                
                yuruyen_direnc = float(df_fx['Direnç_S1'].iloc[-1])
                yuruyen_destek = float(df_fx['Destek_D1'].iloc[-1])
                
                # 5. PRICE ACTION SINIFLANDIRICI KATMANI
                son_mum_high = float(df_fx['High'].iloc[-1])
                son_mum_low = float(df_fx['Low'].iloc[-1])
                son_mum_open = float(df_fx['Open'].iloc[-1])
                son_mum_close = float(df_fx['Close'].iloc[-1])
                
                onceki_mum_high = float(df_fx['High'].iloc[-2])
                onceki_mum_low = float(df_fx['Low'].iloc[-2])
                onceki_mum_open = float(df_fx['Open'].iloc[-2])
                onceki_mum_close = float(df_fx['Close'].iloc[-2])
                
                mum_boyu = son_mum_high - son_mum_low
                alt_fitil = min(son_mum_open, son_mum_close) - son_mum_low
                ust_fitil = son_mum_high - max(son_mum_open, son_mum_close)
                
                is_bullish_pin = (alt_fitil / mum_boyu) > 0.60 if mum_boyu > 0 else False
                is_bearish_pin = (ust_fitil / mum_boyu) > 0.60 if mum_boyu > 0 else False
                is_bullish_engulfing = (onceki_mum_close < onceki_mum_open) and (son_mum_close > son_mum_open) and (son_mum_close > onceki_mum_open)
                is_bearish_engulfing = (onceki_mum_close > onceki_mum_open) and (son_mum_close < son_mum_open) and (son_mum_close < onceki_mum_open)
                
                son_ekstrem_zirve = df_fx['High'].tail(15).iloc[:-1].max()
                son_ekstrem_dip = df_fx['Low'].tail(15).iloc[:-1].min()
                is_msb_bullish = son_fiyat > son_ekstrem_zirve
                is_msb_bearish = son_fiyat < son_ekstrem_dip

                # 6. ÇİFT YÖNLÜ KARAR MOTORU (HIBRIIT DESTEK/DİRENÇ ENTEGRELİ)
                long_skor = 0.0
                short_skor = 0.0
                nedenler = []
                
                if son_fiyat > b_ust:
                    long_skor += 3.5; nedenler.append("🟩 KRİSTAL BOX: Üst band yukarı yönlü kırıldı (Long +3.5)")
                elif son_fiyat < b_alt:
                    short_skor += 3.5; nedenler.append("🟥 KRİSTAL BOX: Alt band aşağı yönlü kırıldı (Short +3.5)")
                else:
                    long_skor += 0.5; short_skor += 0.5; nedenler.append("🟨 KRİSTAL BOX: Fiyat kutu içinde konsolide oluyor (Nötr +0.5)")
                
                # Yürüyen Seviye Tetik Kontrolleri (+1.0)
                if son_fiyat > yuruyen_direnc:
                    long_skor += 1.0; nedenler.append(f"🎯 MOMENTUM: {yuruyen_direnc:.4f} Anlık Direnci yukarı aşıldı (Long +1.0)")
                elif son_fiyat < yuruyen_destek:
                    short_skor += 1.0; nedenler.append(f"🎯 MOMENTUM: {yuruyen_destek:.4f} Anlık Desteği aşağı yönlü patladı (Short +1.0)")
                
                # 🏛️ ASIL SABİT KALE KONTROLÜ (Ekstra Güven Onayı +1.0)
                if son_fiyat > asıl_direnc_kale:
                    long_skor += 1.0; nedenler.append(f"🏰 ASIL KALE YIKILDI: {asıl_direnc_kale:.4f} Sabit Ana Direnci yukarı geçildi! (Long +1.0)")
                elif son_fiyat < asıl_destek_kale:
                    short_skor += 1.0; nedenler.append(f"🏰 ASIL KALE YIKILDI: {asıl_destek_kale:.4f} Sabit Ana Desteği aşağı yönlü kırıldı! (Short +1.0)")
                    
                if son_fiyat > ema21 and ema21 > ema50:
                    long_skor += 2.0; nedenler.append("🟩 GANN/TREND: EMA'lar boğa diziliminde ve fiyat üstünde (Long +2.0)")
                elif son_fiyat < ema21 and ema21 < ema50:
                    short_skor += 2.0; nedenler.append("🟥 GANN/TREND: EMA'lar ayı diziliminde ve fiyat altında (Short +2.0)")
                else:
                    nedenler.append("🟨 GANN/TREND: Hareketli ortalamalar kararsız bölgede")
                    
                if 50 < rsi_val < 70: long_skor += 1.5
                elif 30 < rsi_val <= 50: short_skor += 1.5
                elif rsi_val >= 70: short_skor += 1.0
                elif rsi_val <= 30: long_skor += 1.0

                if is_bullish_pin: long_skor += 1.0; nedenler.append("🔥 PRICE ACTION: Boğa Pin Bar oluştu")
                if is_bullish_engulfing: long_skor += 1.0; nedenler.append("🔥 PRICE ACTION: Bullish Engulfing görüldü")
                if is_msb_bullish: long_skor += 1.0; nedenler.append("⚔️ PRICE ACTION: Market Yapısı Boğa yönlü kırıldı (MSB/CHoCH)")
                    
                if is_bearish_pin: short_skor += 1.0; nedenler.append("❄️ PRICE ACTION: Ayı Pin Bar oluştu")
                if is_bearish_engulfing: short_skor += 1.0; nedenler.append("❄️ PRICE ACTION: Bearish Engulfing görüldü")
                if is_msb_bearish: short_skor += 1.0; nedenler.append("⚔️ PRICE ACTION: Market Yapısı Ayı yönlü kırıldı (MSB/CHoCH)")

                long_skor = min(10.0, round(long_skor, 1))
                short_skor = min(10.0, round(short_skor, 1))

                anlik_algoritma_yonu = "NÖTR (İZLE)"
                if long_skor >= 7.0 and long_skor >= short_skor: anlik_algoritma_yonu = "LONG (YUKARI)"
                elif short_skor >= 7.0 and short_skor > long_skor: anlik_algoritma_yonu = "SHORT (AŞAĞI)"

                # Listeye ana sayfada sıralanabilmesi için sonuçları ekliyoruz
                hibrit_hesap = max(long_skor, short_skor)
                sonuclar.append({
                    "Enstrüman": asset_adi, "Anlık Fiyat": son_fiyat, "Yön": anlik_algoritma_yonu,
                    "Long Skor": long_skor, "Short Skor": short_skor, "Hibrit Skor": hibrit_hesap, "RSI": rsi_val
                })

                # AKILLI BELLEK KİLİTLEME & ARKA PLAN TELEGRAM BİLDİRİM TETİKLEYİCİ
                if anlik_algoritma_yonu != "NÖTR (İZLE)" and st.session_state[state_sinyal_key] == "NÖTR (İZLE)":
                    st.session_state[state_sinyal_key] = anlik_algoritma_yonu
                    st.session_state[state_fiyat_key] = son_fiyat
                    
                    hedef_tp = son_fiyat + (atr_val * 2.0) if anlik_algoritma_yonu == "LONG (YUKARI)" else son_fiyat - (atr_val * 2.0)
                    risk_sl = son_fiyat - (atr_val * 1) if anlik_algoritma_yonu == "LONG (YUKARI)" else son_fiyat + (atr_val * 1)
                    skor_val = long_skor if anlik_algoritma_yonu == "LONG (YUKARI)" else short_skor
                    emoji = "🚀" if anlik_algoritma_yonu == "LONG (YUKARI)" else "💥"
                    
                    mesaj_metni = (
                        f"{emoji} *OTONOM KIRILIM BİLDİRİMİ*\n\n"
                        f"**Enstrüman:** {asset_adi}\n"
                        f"**Strateji Yönü:** {anlik_algoritma_yonu}\n"
                        f"**Giriş Seviyesi:** `{son_fiyat:.4f}`\n"
                        f"**🏰 ASIL SABİT DİRENÇ:** `{asıl_direnc_kale:.4f}`\n"
                        f"**🏰 ASIL SABİT DESTEK:** `{asıl_destek_kale:.4f}`\n"
                        f"**Hedef (TP):** `{hedef_tp:.4f}`\n"
                        f"**Zarar Kes (SL):** `{risk_sl:.4f}`\n"
                        f"**Sistem Güven Skoru:** `{skor_val}/10`"
                    )
                    telegram_sinyal_gonder(mesaj_metni)
                    
                elif anlik_algoritma_yonu == "NÖTR (İZLE)":
                    st.session_state[state_sinyal_key] = "NÖTR (İZLE)"
                    st.session_state[state_fiyat_key] = 0.0

                # 🖥️ EKRANDA O AN SEÇİLİ OLAN ENSTRÜMANIN DETAYLI GÖRSEL GÖSTERİMİ
                if asset_adi == secilen_forex_adi:
                    strateji_yonu = st.session_state[state_sinyal_key]
                    
                    if strateji_yonu == "LONG (YUKARI)":
                        ana_skor = long_skor; durum_color = "#2ECC71"; sinyal_tetik_fiyati = st.session_state[state_fiyat_key]
                        durum_msg = f"🚀 GÜÇLÜ BOĞA - {sinyal_tetik_fiyati:.4f} SEVİYESİNDEN SİNYAL SABİTLENDİ"
                        sl_noktasi = sinyal_tetik_fiyati - (atr_val * 1); tp_noktasi = sinyal_tetik_fiyati + (atr_val * 2.0)
                    elif strateji_yonu == "SHORT (AŞAĞI)":
                        ana_skor = short_skor; durum_color = "#E74C3C"; sinyal_tetik_fiyati = st.session_state[state_fiyat_key]
                        durum_msg = f"💥 GÜÇLÜ AYI - {sinyal_tetik_fiyati:.4f} SEVİYESİNDEN AÇIĞA SATIŞ SABİTLENDİ"
                        sl_noktasi = sinyal_tetik_fiyati + (atr_val * 1); tp_noktasi = sinyal_tetik_fiyati - (atr_val * 2.0)
                    else:
                        ana_skor = max(long_skor, short_skor); durum_color = "#F1C40F"; sinyal_tetik_fiyati = son_fiyat
                        durum_msg = "🟡 TEST BÖLGESİ - BELİRLİ BİR SEVİYE KIRILIMI BEKLENİYOR"
                        sl_noktasi = son_fiyat - (atr_val * 2.0); tp_noktasi = son_fiyat + (atr_val * 2.0)

                    # Savaş Kartı Gösterimi
                    st.markdown(f"""
                        <div style="background-color: {durum_color}; padding: 25px; border-radius: 15px; text-align: center; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.15);">
                            <h1 style="color: #FFFFFF !important; border: none; margin: 0; font-size: 2.2rem;">{asset_adi} // DETAYLI CANLI MONITOR</h1>
                            <h3 style="color: #FFFFFF !important; border: none; margin: 8px 0 0 0; font-weight: 800;">{durum_msg} (Sistem Güven Skoru: {ana_skor:.1f}/10)</h3>
                        </div>
                    """, unsafe_allow_html=True)

                    # ÇİFT FİYAT DESTEKLİ METRIC SENSÖRLERİ
                    f1, f2, f3, f4, f5 = st.columns(5)
                    if strateji_yonu != "NÖTR (İZLE)":
                        f1.metric("🎯 SİNYAL GİRİŞİ (SABİT)", f"{sinyal_tetik_fiyati:.4f}")
                        f2.metric("⚡ ANLIK FİYAT (CANLI)", f"{son_fiyat:.4f}", delta=f"{son_fiyat - sinyal_tetik_fiyati:.4f}")
                    else:
                        f1.metric("ANLIK FİYAT", f"{son_fiyat:.4f}")
                        f2.metric("GİRİŞ DURUMU", "BEKLEMEDE")
                        
                    f3.metric("OYNK_ALANI (ATR)", f"{atr_val:.4f}")
                    f4.metric("🎯 OTONOM TP", f"{tp_noktasi:.4f}")
                    f5.metric("🛑 OTONOM SL", f"{sl_noktasi:.4f}")

                    # PANEL YERLEŞİMİ (Sol: İstatistikler | Sağ: Gelişmiş Plotly)
                    sol_p, sag_p = st.columns([1, 2])
                    
                    with sol_p:
                        st.markdown("### 🧠 Çift Yönlü Sistem Ortalaması")
                        st.markdown(f"**🟢 Long Algoritma Ağırlığı:** `{long_skor} / 10`")
                        st.markdown(f"""<div style="width: 100%; background-color: #E0E0E0; height: 8px; border-radius: 4px; margin-bottom: 12px;"><div style="width: {int(long_skor*10)}%; background-color: #2ECC71; height: 100%; border-radius: 4px;"></div></div>""", unsafe_allow_html=True)
                        st.markdown(f"**🔴 Short Algoritma Ağırlığı:** `{short_skor} / 10`")
                        st.markdown(f"""<div style="width: 100%; background-color: #E0E0E0; height: 8px; border-radius: 4px; margin-bottom: 20px;"><div style="width: {int(short_skor*10)}%; background-color: #E74C3C; height: 100%; border-radius: 4px;"></div></div>""", unsafe_allow_html=True)
                        
                        st.markdown("#### 🔍 Sinyal Gerekçeleri")
                        for neden in nedenler: st.write(f"- {neden}")
                            
                        st.markdown("#### 🔬 Teknik Değerler")
                        st.write(f"**RSI Göstergesi:** {rsi_val:.2f}")
                        
                        st.markdown("#### 🏰 Asıl Kaleler (Sabit)")
                        st.error(f"**🏰 Ana Direniş Hattı:** `{asıl_direnc_kale:.4f}`")
                        st.info(f"**🏰 Ana Güvenlik Üssü (Destek):** `{asıl_destek_kale:.4f}`")

                    with sag_p:
                        st.markdown("### 📈 Çift Yönlü Grafik ve Hedef Haritası")
# =================================================================================
# =================================================================================
# ÇEKİRDEK 3: FOREX & KÜRESEL PİYASALAR (TAM OTONOM ÇOKLU ENSTRÜMAN RADARI - ASIL SABİT DESTEK/DİRENÇLİ)
# =================================================================================
elif calisma_modu == "Forex & Küresel Piyasalar (Çift Yönlü)":
    import datetime
    
    # 🗓️ 1. HAFTA SONU VE PİYASA KAPANIŞ KİLİDİ (ESKİ VERİ VE YALAN SİNYAL ENGELLEYİCİ)
    simdi = datetime.datetime.now()
    haftanin_gunu = simdi.weekday() # 0=Pazartesi, 4=Cuma, 5=Cumartesi, 6=Pazar
    saat = simdi.hour
    
    piyasa_kapali = False
    if haftanin_gunu == 5 or haftanin_gunu == 6: # Cumartesi veya Pazar
        piyasa_kapali = True
    elif haftanin_gunu == 4 and saat >= 23: # Cuma gecesi 23:00 sonrası
        piyasa_kapali = True
    elif haftanin_gunu == 0 and saat < 1: # Pazartesi gece yarısı açılış öncesi
        piyasa_kapali = True

    if piyasa_kapali:
        st.warning("💤 Küresel Piyasalar Hafta Sonu Arasına Girmiştir. Eski verilerin dönmesini ve yalan sinyal üretimini engellemek için akış Pazartesi açılışına kadar durduruldu.")
        st.stop()

    # Piyasa açıksa 1 dakikada bir sayfayı yeniler
    st_autorefresh(interval=60000, key="global_forex_multi_scan_v15_final_sabit_kaleler")
    st.markdown("## 🌐 ÇİFT YÖNLÜ OTONOM FOREX KOMUTA MERKEZİ (TÜM LİSTE ARKA PLANDA TARANIYOR)")
    
    # -----------------------------------------------------------------------------
    # TELEGRAM ENTEGRASYON BÖLÜMÜ
    # -----------------------------------------------------------------------------
    TELEGRAM_BOT_TOKEN = "8817119197:AAHcHADLXZ7DbLgJp7yskg94QO0Q6jJd85s"
    TELEGRAM_CHAT_ID = "1338802399"

    def telegram_sinyal_gonder(mesaj):
        """Kırılım anında Telegram üzerinden anlık bildirim atar."""
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            try:
                import requests
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mesaj, "parse_mode": "Markdown"}
                requests.post(url, json=payload, timeout=5)
            except Exception as e:
                pass 

    # 🛡️ YAHOO ENGELİNİ AŞAN AKILLI ÖNBELLEK MOTORU (VERİLERİN ESKİDE KALMASINI ENGELLER)
    @st.cache_data(ttl=300, show_spinner=False)
    def get_yahoo_clean_data(ticker):
        try:
            df = yf.download(tickers=ticker, period="1mo", interval="1h", progress=False)
            return df
        except:
            return pd.DataFrame()

    # SEKMELİ YAPI (Grafik Paneli ve Geniş Haber Paneli Ayrımı)
    fx_tab1, fx_tab2 = st.tabs(["📊 Otonom Teknik Analiz & PA", "📅 Canlı Ekonomik Takvim & Makro Etki"])
    
    with fx_tab2:
        st.markdown("### 📰 Küresel Makroekonomik Takvim (Maksimum Genişlik & Türkçe)")
        st.warning("⚠️ **Volatilite Uyarısı:** Yüksek etkili (3 Yıldızlı / Kırmızı) verilerin açıklanma saatlerinde teknik indikatörler devredışı kalabilir. Haber saatinden 15 dk önce ve sonra işlem riskini minimuma indirin.")
        
        ekonomik_takvim_html = """
        <div style="position: relative; width: 100%; margin: 0; padding: 0;">
            <style>
                html, body { margin: 0; padding: 0; overflow-x: hidden; }
                .tradingview-widget-container { width: 100% !important; height: 900px !important; }
            </style>
            <div class="tradingview-widget-container">
              <div class="tradingview-widget-container__widget" style="width: 100%; height: 100%;"></div>
              <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
              {
              "colorTheme": "light",
              "isWidescreen": true,
              "width": "100%",
              "height": "100%",
              "locale": "tr",
              "importanceFilter": "-1,0,1",
              "countryFilter": "us,eu,gb,jp,ch,ca,au,tr"
              }
              </script>
            </div>
        </div>
        """
        st.components.v1.html(ekonomik_takvim_html, height=950, scrolling=True)
        
    with fx_tab1:
        # Sabit Test Butonu
        if st.button("🚀 Sistem Bildirim Testini Tetikle"):
            try:
                import requests
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                payload = {"chat_id": TELEGRAM_CHAT_ID, "text": "🎯 *SİSTEM TESTİ BAŞARILI!*\n\nAsıl Sabit Kaleli çoklu tarama modunda Telegram hattınız aktiftir.", "parse_mode": "Markdown"}
                response = requests.post(url, json=payload, timeout=5)
                if response.status_code == 200: st.success("🎯 Harika! Mesaj başarıyla gönderildi. Telefonunu kontrol et.")
                else: st.error(f"❌ Telegram API Hata Döndürdü: {response.text}")
            except Exception as e: st.error(f"🚨 Sunucu/Ağ Bağlantı Hatası: {e}")

        st.info("🔄 **7/24 Arka Plan Tarayıcısı Aktif:** Grafik üzerinde kalın düz çizgiler ASIL SABİT kaleleri, kesikli ince çizgiler ise yürüyen anlık momentum seviyelerini gösterir.")
        
        secilen_forex_adi = st.selectbox("Ekranda Detaylı İncelemek İstediğiniz Küresel Enstrüman:", list(forex_assets.keys()))
        sonuclar = []

        # 🤖 OTONOM ÇOKLU TARAMA DÖNGÜSÜ
        for asset_adi, asset_ticker in forex_assets.items():
            
            state_sinyal_key = f"fx_state_yon_{asset_adi}"
            state_fiyat_key = f"fx_lock_price_{asset_adi}"
            
            if state_sinyal_key not in st.session_state: st.session_state[state_sinyal_key] = "NÖTR (İZLE)"
            if state_fiyat_key not in st.session_state: st.session_state[state_fiyat_key] = 0.0
            
            # Korumalı ve önbellekli fonksiyon çağrısı
            df_fx = get_yahoo_clean_data(asset_ticker)
                
            if not df_fx.empty and len(df_fx) > 25:
                if isinstance(df_fx.columns, pd.MultiIndex): 
                    df_fx.columns = df_fx.columns.get_level_values(0)
                df_fx.columns = [str(c).strip().capitalize() for c in df_fx.columns]
                
                if hasattr(df_fx['Open'], 'columns') or (type(df_fx['Open']).__name__ == 'DataFrame'): df_fx['Open'] = df_fx['Open'].iloc[:, 0]
                if hasattr(df_fx['High'], 'columns') or (type(df_fx['High']).__name__ == 'DataFrame'): df_fx['High'] = df_fx['High'].iloc[:, 0]
                if hasattr(df_fx['Low'], 'columns') or (type(df_fx['Low']).__name__ == 'DataFrame'): df_fx['Low'] = df_fx['Low'].iloc[:, 0]
                if hasattr(df_fx['Close'], 'columns') or (type(df_fx['Close']).__name__ == 'DataFrame'): df_fx['Close'] = df_fx['Close'].iloc[:, 0]
                
                # 🏃 1. DİNAMİK/YÜRÜYEN SEVİYELER (Momentum Takibi - Son 15 Mum)
                df_fx['Direnç_S1'] = df_fx['High'].rolling(window=15).max().shift(1)
                df_fx['Destek_D1'] = df_fx['Low'].rolling(window=15).min().shift(1)
                
                # 🏛️ 2. ASIL SABİT PSİKOLOJİK KALELER (Geniş Zamanlı Klasik Pivot Kümesi)
                gecmis_high = df_fx['High'].tail(24).max()
                gecmis_low = df_fx['Low'].tail(24).min()
                gecmis_close = df_fx['Close'].tail(24).mean()
                
                sabit_pivot = (gecmis_high + gecmis_low + gecmis_close) / 3
                asıl_direnc_kale = (2 * sabit_pivot) - gecmis_low
                asıl_destek_kale = (2 * sabit_pivot) - gecmis_high
                
                # 3. Kristal Box Hesaplamaları (Donchian)
                df_fx['box_ust'] = df_fx['High'].rolling(window=20).max()
                df_fx['box_alt'] = df_fx['Low'].rolling(window=20).min()
                df_fx['box_orta'] = (df_fx['box_ust'] + df_fx['box_alt']) / 2
                
                # 4. Native ATR & Teknik İndikatör Hesaplamaları
                high_low = df_fx['High'] - df_fx['Low']
                high_close = (df_fx['High'] - df_fx['Close'].shift()).abs()
                low_close = (df_fx['Low'] - df_fx['Close'].shift()).abs()
                ranges = pd.concat([high_low, high_close, low_close], axis=1)
                true_range = ranges.max(axis=1)
                df_fx['ATR'] = true_range.ewm(alpha=1/14, adjust=False).mean()
                
                fx_delta = df_fx['Close'].diff()
                fx_gain = fx_delta.clip(lower=0)
                fx_loss = -fx_delta.clip(upper=0)
                fx_avg_gain = fx_gain.ewm(com=13, adjust=False).mean()
                fx_avg_loss = fx_loss.ewm(com=13, adjust=False).mean()
                fx_rs = fx_avg_gain / fx_avg_loss
                df_fx['RSI'] = 100 - (100 / (1 + fx_rs))
                
                df_fx['EMA21'] = df_fx['Close'].ewm(span=21, adjust=False).mean()
                df_fx['EMA50'] = df_fx['Close'].ewm(span=50, adjust=False).mean()
                
                son_fiyat = float(df_fx['Close'].iloc[-1])
                atr_val = float(df_fx['ATR'].iloc[-1])
                rsi_val = float(df_fx['RSI'].iloc[-1])
                b_ust = float(df_fx['box_ust'].iloc[-2])
                b_alt = float(df_fx['box_alt'].iloc[-2])
                ema21 = float(df_fx['EMA21'].iloc[-1])
                ema50 = float(df_fx['EMA50'].iloc[-1])
                
                yuruyen_direnc = float(df_fx['Direnç_S1'].iloc[-1])
                yuruyen_destek = float(df_fx['Destek_D1'].iloc[-1])
                
                # 5. PRICE ACTION SINIFLANDIRICI KATMANI
                son_mum_high = float(df_fx['High'].iloc[-1])
                son_mum_low = float(df_fx['Low'].iloc[-1])
                son_mum_open = float(df_fx['Open'].iloc[-1])
                son_mum_close = float(df_fx['Close'].iloc[-1])
                
                onceki_mum_high = float(df_fx['High'].iloc[-2])
                onceki_mum_low = float(df_fx['Low'].iloc[-2])
                onceki_mum_open = float(df_fx['Open'].iloc[-2])
                onceki_mum_close = float(df_fx['Close'].iloc[-2])
                
                mum_boyu = son_mum_high - son_mum_low
                alt_fitil = min(son_mum_open, son_mum_close) - son_mum_low
                ust_fitil = son_mum_high - max(son_mum_open, son_mum_close)
                
                is_bullish_pin = (alt_fitil / mum_boyu) > 0.60 if mum_boyu > 0 else False
                is_bearish_pin = (ust_fitil / mum_boyu) > 0.60 if mum_boyu > 0 else False
                is_bullish_engulfing = (onceki_mum_close < onceki_mum_open) and (son_mum_close > son_mum_open) and (son_mum_close > onceki_mum_open)
                is_bearish_engulfing = (onceki_mum_close > onceki_mum_open) and (son_mum_close < son_mum_open) and (son_mum_close < onceki_mum_open)
                
                son_ekstrem_zirve = df_fx['High'].tail(15).iloc[:-1].max()
                son_ekstrem_dip = df_fx['Low'].tail(15).iloc[:-1].min()
                is_msb_bullish = son_fiyat > son_ekstrem_zirve
                is_msb_bearish = son_fiyat < son_ekstrem_dip

                # 6. ÇİFT YÖNLÜ KARAR MOTORU
                long_skor = 0.0
                short_skor = 0.0
                nedenler = []
                
                if son_fiyat > b_ust:
                    long_skor += 3.5; nedenler.append("🟩 KRİSTAL BOX: Üst band yukarı yönlü kırıldı (Long +3.5)")
                elif son_fiyat < b_alt:
                    short_skor += 3.5; nedenler.append("🟥 KRİSTAL BOX: Alt band aşağı yönlü kırıldı (Short +3.5)")
                else:
                    long_skor += 0.5; short_skor += 0.5; nedenler.append("🟨 KRİSTAL BOX: Fiyat kutu içinde konsolide oluyor (Nötr +0.5)")
                
                if son_fiyat > yuruyen_direnc:
                    long_skor += 1.0; nedenler.append(f"🎯 MOMENTUM: {yuruyen_direnc:.4f} Anlık Direnci yukarı aşıldı (Long +1.0)")
                elif son_fiyat < yuruyen_destek:
                    short_skor += 1.0; nedenler.append(f"🎯 MOMENTUM: {yuruyen_destek:.4f} Anlık Desteği aşağı yönlü patladı (Short +1.0)")
                
                if son_fiyat > asıl_direnc_kale:
                    long_skor += 1.0; nedenler.append(f"🏰 ASIL KALE YIKILDI: {asıl_direnc_kale:.4f} Sabit Ana Direnci yukarı geçildi! (Long +1.0)")
                elif son_fiyat < asıl_destek_kale:
                    short_skor += 1.0; nedenler.append(f"🏰 ASIL KALE YIKILDI: {asıl_destek_kale:.4f} Sabit Ana Desteği aşağı yönlü kırıldı! (Short +1.0)")
                    
                if son_fiyat > ema21 and ema21 > ema50:
                    long_skor += 2.0; nedenler.append("🟩 GANN/TREND: EMA'lar boğa diziliminde ve fiyat üstünde (Long +2.0)")
                elif son_fiyat < ema21 and ema21 < ema50:
                    short_skor += 2.0; nedenler.append("🟥 GANN/TREND: EMA'lar ayı diziliminde ve fiyat altında (Short +2.0)")
                else:
                    nedenler.append("🟨 GANN/TREND: Hareketli ortalamalar kararsız bölgede")
                    
                if 50 < rsi_val < 70: long_skor += 1.5
                elif 30 < rsi_val <= 50: short_skor += 1.5
                elif rsi_val >= 70: short_skor += 1.0
                elif rsi_val <= 30: long_skor += 1.0

                if is_bullish_pin: long_skor += 1.0; nedenler.append("🔥 PRICE ACTION: Boğa Pin Bar oluştu")
                if is_bullish_engulfing: long_skor += 1.0; nedenler.append("🔥 PRICE ACTION: Bullish Engulfing görüldü")
                if is_msb_bullish: long_skor += 1.0; nedenler.append("⚔️ PRICE ACTION: Market Yapısı Boğa yönlü kırıldı (MSB/CHoCH)")
                    
                if is_bearish_pin: short_skor += 1.0; nedenler.append("❄️ PRICE ACTION: Ayı Pin Bar oluştu")
                if is_bearish_engulfing: short_skor += 1.0; nedenler.append("❄️ PRICE ACTION: Bearish Engulfing görüldü")
                if is_msb_bearish: short_skor += 1.0; nedenler.append("⚔️ PRICE ACTION: Market Yapısı Ayı yönlü kırıldı (MSB/CHoCH)")

                long_skor = min(10.0, round(long_skor, 1))
                short_skor = min(10.0, round(short_skor, 1))

                anlik_algoritma_yonu = "NÖTR (İZLE)"
                if long_skor >= 7.0 and long_skor >= short_skor: anlik_algoritma_yonu = "LONG (YUKARI)"
                elif short_skor >= 7.0 and short_skor > long_skor: anlik_algoritma_yonu = "SHORT (AŞAĞI)"

                hibrit_hesap = max(long_skor, short_skor)
                sonuclar.append({
                    "Enstrüman": asset_adi, "Anlık Fiyat": son_fiyat, "Yön": anlik_algoritma_yonu,
                    "Long Skor": long_skor, "Short Skor": short_skor, "Hibrit Skor": hibrit_hesap, "RSI": rsi_val
                })

                # AKILLI BELLEK KİLİTLEME & ARKA PLAN TELEGRAM BİLDİRİM TETİKLEYİCİ (TAM 1'E 2 PİYASA STANDARDI)
                if anlik_algoritma_yonu != "NÖTR (İZLE)" and st.session_state[state_sinyal_key] == "NÖTR (İZLE)":
                    st.session_state[state_sinyal_key] = anlik_algoritma_yonu
                    st.session_state[state_fiyat_key] = son_fiyat
                    
                    # 🎯 HEDEFLERİ 1'E 2 ORANINA SABİTLEDİK (SL: 1.0 ATR | TP: 2.0 ATR)
                    hedef_tp = son_fiyat + (atr_val * 2.0) if anlik_algoritma_yonu == "LONG (YUKARI)" else son_fiyat - (atr_val * 2.0)
                    risk_sl = son_fiyat - (atr_val * 1.0) if anlik_algoritma_yonu == "LONG (YUKARI)" else son_fiyat + (atr_val * 1.0)
                    skor_val = long_skor if anlik_algoritma_yonu == "LONG (YUKARI)" else short_skor
                    emoji = "🚀" if anlik_algoritma_yonu == "LONG (YUKARI)" else "💥"
                    
                    mesaj_metni = (
                        f"{emoji} *OTONOM KIRILIM BİLDİRİMİ*\n\n"
                        f"**Enstrüman:** {asset_adi}\n"
                        f"**Strateji Yönü:** {anlik_algoritma_yonu}\n"
                        f"**Giriş Seviyesi:** `{son_fiyat:.4f}`\n"
                        f"**🏰 ASIL SABİT DİRENÇ:** `{asıl_direnc_kale:.4f}`\n"
                        f"**🏰 ASIL SABİT DESTEK:** `{asıl_destek_kale:.4f}`\n"
                        f"**Hedef (TP):** `{hedef_tp:.4f}`\n"
                        f"**Zarar Kes (SL):** `{risk_sl:.4f}`\n"
                        f"**Sistem Güven Skoru:** `{skor_val}/10`"
                    )
                    telegram_sinyal_gonder(mesaj_metni)
                    
                elif anlik_algoritma_yonu == "NÖTR (İZLE)":
                    st.session_state[state_sinyal_key] = "NÖTR (İZLE)"
                    st.session_state[state_fiyat_key] = 0.0

                # 🖥️ EKRANDA O AN SEÇİLİ OLAN ENSTRÜMANIN DETAYLI GÖRSEL GÖSTERİMİ
                if asset_adi == secilen_forex_adi:
                    strateji_yonu = st.session_state[state_sinyal_key]
                    
                    if strateji_yonu == "LONG (YUKARI)":
                        ana_skor = long_skor; durum_color = "#2ECC71"; sinyal_tetik_fiyati = st.session_state[state_fiyat_key]
                        durum_msg = f"🚀 GÜÇLÜ BOĞA - {sinyal_tetik_fiyati:.4f} SEVİYESİNDEN SİNYAL SABİTLENDİ"
                        # EKRAN GRAFİK MATEMATİĞİ ENTEGRASYONU (1'E 2 AYARI)
                        sl_noktasi = sinyal_tetik_fiyati - (atr_val * 1.0)
                        tp_noktasi = sinyal_tetik_fiyati + (atr_val * 2.0)
                    elif strateji_yonu == "SHORT (AŞAĞI)":
                        ana_skor = short_skor; durum_color = "#E74C3C"; sinyal_tetik_fiyati = st.session_state[state_fiyat_key]
                        durum_msg = f"💥 GÜÇLÜ AYI - {sinyal_tetik_fiyati:.4f} SEVİYESİNDEN AÇIĞA SATIŞ SABİTLENDİ"
                        # EKRAN GRAFİK MATEMATİĞİ ENTEGRASYONU (1'E 2 AYARI)
                        sl_noktasi = sinyal_tetik_fiyati + (atr_val * 1.0)
                        tp_noktasi = sinyal_tetik_fiyati - (atr_val * 2.0)
                    else:
                        ana_skor = max(long_skor, short_skor); durum_color = "#F1C40F"; sinyal_tetik_fiyati = son_fiyat
                        durum_msg = "🟡 TEST BÖLGESİ - BELİRLİ BİR SEVİYE KIRILIMI BEKLENİYOR"
                        sl_noktasi = son_fiyat - (atr_val * 1.5)
                        tp_noktasi = son_fiyat + (atr_val * 1.5)

                    st.markdown(f"""
                        <div style="background-color: {durum_color}; padding: 25px; border-radius: 15px; text-align: center; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.15);">
                            <h1 style="color: #FFFFFF !important; border: none; margin: 0; font-size: 2.2rem;">{asset_adi} // DETAYLI CANLI MONITOR</h1>
                            <h3 style="color: #FFFFFF !important; border: none; margin: 8px 0 0 0; font-weight: 800;">{durum_msg} (Sistem Güven Skoru: {ana_skor:.1f}/10)</h3>
                        </div>
                    """, unsafe_allow_html=True)

                    f1, f2, f3, f4, f5 = st.columns(5)
                    if strateji_yonu != "NÖTR (İZLE)":
                        f1.metric("🎯 SİNYAL GİRİŞİ (SABİT)", f"{sinyal_tetik_fiyati:.4f}")
                        f2.metric("⚡ ANLIK FİYAT (CANLI)", f"{son_fiyat:.4f}", delta=f"{son_fiyat - sinyal_tetik_fiyati:.4f}")
                    else:
                        f1.metric("ANLIK FİYAT", f"{son_fiyat:.4f}")
                        f2.metric("GİRİŞ DURUMU", "BEKLEMEDE")
                        
                    f3.metric("OYNK_ALANI (ATR)", f"{atr_val:.4f}")
                    f4.metric("🎯 OTONOM TP", f"{tp_noktasi:.4f}")
                    f5.metric("🛑 OTONOM SL", f"{sl_noktasi:.4f}")

                    sol_p, sag_p = st.columns([1, 2])
                    
                    with sol_p:
                        st.markdown("### 🧠 Çift Yönlü Sistem Ortalaması")
                        st.markdown(f"**🟢 Long Algoritma Ağırlığı:** `{long_skor} / 10`")
                        st.markdown(f"""<div style="width: 100%; background-color: #E0E0E0; height: 8px; border-radius: 4px; margin-bottom: 12px;"><div style="width: {int(long_skor*10)}%; background-color: #2ECC71; height: 100%; border-radius: 4px;"></div></div>""", unsafe_allow_html=True)
                        st.markdown(f"**🔴 Short Algoritma Ağırlığı:** `{short_skor} / 10`")
                        st.markdown(f"""<div style="width: 100%; background-color: #E0E0E0; height: 8px; border-radius: 4px; margin-bottom: 20px;"><div style="width: {int(short_skor*10)}%; background-color: #E74C3C; height: 100%; border-radius: 4px;"></div></div>""", unsafe_allow_html=True)
                        
                        st.markdown("#### 🔍 Sinyal Gerekçeleri")
                        for neden in nedenler: st.write(f"- {neden}")
                            
                        st.markdown("#### 🔬 Teknik Değerler")
                        st.write(f"**RSI Göstergesi:** {rsi_val:.2f}")
                        
                        st.markdown("#### 🏰 Asıl Kaleler (Sabit)")
                        st.error(f"**🏰 Ana Direniş Hattı:** `{asıl_direnc_kale:.4f}`")
                        st.info(f"**🏰 Ana Güvenlik Üssü (Destek):** `{asıl_destek_kale:.4f}`")

                    with sag_p:
                        st.markdown("### 📈 Çift Yönlü Grafik ve Hedef Haritası")
                        fig_fx = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.06, row_heights=[0.7, 0.3])
                        fig_fx.add_trace(go.Candlestick(x=df_fx.index, open=df_fx['Open'], high=df_fx['High'], low=df_fx['Low'], close=df_fx['Close'], name="Fiyat"), row=1, col=1)
                        
                        fig_fx.add_trace(go.Scatter(x=df_fx.index, y=[asıl_direnc_kale]*len(df_fx), line=dict(color='#8B0000', width=3.5, dash='solid'), name="🏰 ASIL DİRENÇ KALESİ"), row=1, col=1)
                        fig_fx.add_trace(go.Scatter(x=df_fx.index, y=[asıl_destek_kale]*len(df_fx), line=dict(color='#006400', width=3.5, dash='solid'), name="🏰 ASIL DESTEK KALESİ"), row=1, col=1)
                        
                        fig_fx.add_trace(go.Scatter(x=df_fx.index, y=df_fx['Direnç_S1'], line=dict(color='#C0392B', width=1.5, dash='dot'), name="🏃 Yürüyen Direnç"), row=1, col=1)
                        fig_fx.add_trace(go.Scatter(x=df_fx.index, y=df_fx['Destek_D1'], line=dict(color='#27AE60', width=1.5, dash='dot'), name="🏃 Yürüyen Destek"), row=1, col=1)
                        
                        fig_fx.add_trace(go.Scatter(x=df_fx.index, y=df_fx['box_ust'], line=dict(color='#8E44AD', width=1.2, dash='dash'), name="Box Üst"), row=1, col=1)
                        fig_fx.add_trace(go.Scatter(x=df_fx.index, y=df_fx['box_alt'], line=dict(color='#8E44AD', width=1.2, dash='dash'), name="Box Alt"), row=1, col=1)
                        fig_fx.add_trace(go.Scatter(x=df_fx.index, y=df_fx['EMA21'], line=dict(color='#E67E22', width=1.0), name="EMA 21"), row=1, col=1)
                        fig_fx.add_trace(go.Scatter(x=df_fx.index, y=df_fx['EMA50'], line=dict(color='#3498DB', width=1.0), name="EMA 50"), row=1, col=1)
                        
                        if strateji_yonu != "NÖTR (İZLE)":
                            fig_fx.add_trace(go.Scatter(x=[df_fx.index[-20], df_fx.index[-1]], y=[tp_noktasi, tp_noktasi], line=dict(color='#2ECC71', width=2.5), name="Hedef (TP)"), row=1, col=1)
                            fig_fx.add_trace(go.Scatter(x=[df_fx.index[-20], df_fx.index[-1]], y=[sl_noktasi, sl_noktasi], line=dict(color='#E74C3C', width=2.5), name="Risk Sınırı (SL)"), row=1, col=1)
                            fig_fx.add_trace(go.Scatter(x=[df_fx.index[-20], df_fx.index[-1]], y=[sinyal_tetik_fiyati, sinyal_tetik_fiyati], line=dict(color='#111111', width=2, dash='dot'), name="Sabit Giriş Seviyesi"), row=1, col=1)
                        
                        fig_fx.add_trace(go.Scatter(x=df_fx.index, y=df_fx['RSI'], line=dict(color='#16A085', width=1.5), name="RSI"), row=2, col=1)
                        fig_fx.update_layout(xaxis_rangeslider_visible=False, height=650, template="plotly_white", margin=dict(l=10, r=10, t=10, b=10))
                        st.plotly_chart(fig_fx, use_container_width=True)

        if sonuclar:
            st.markdown("### 📋 Küresel Piyasalar Anlık Tarama Özeti")
            df_sonuc = pd.DataFrame(sonuclar).sort_values(by="Hibrit Skor", ascending=False).reset_index(drop=True)
            st.dataframe(df_sonuc, use_container_width=True)

# =================================================================================
# ÇEKİRDEK 4: ULTRA FXMATİK (QUANT MATRIX) - DİNAMİK RENKLİ VE SERBEST GRAFİKLİ MOTOR
# =================================================================================
elif calisma_modu ==  "Ultra FXMatik (Quant Matrix)":
    st.markdown("## 🦅 ULTRA FXMATİK (QUANT MATRIX COMPASS)")
    st.markdown("---")
    
    import numpy as np
    import pandas as pd
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    # ⚙️ Gelişmiş Ayar Paneli (Sidebar)
    with st.sidebar:
        st.markdown("### 📊 GLOBAL ENSTRÜMAN SEÇİMİ")
        
        makro_evren = {
            "ONS ALTIN": "GC=F",
            "ONS GÜMÜŞ": "SI=F",
            "ONS BAKIR" : "HG=F",
            "ONS PALADYUM": "PA=F",
            "ONS PLATİN": "PL=F",
            "WTI HAM PETROL": "CL=F",
            "BRENT PETROL": "BZ=F",
            "EUR / USD": "EURUSD=X",
            "GBP / USD": "GBPUSD=X",
            "USD / JPY": "USDJPY=X",
            "AUD / USD": "AUDUSD=X",
            "USD / CAD": "USDCAD=X",
            "USD / CHF": "USDCHF=X",
            "S&P 500": "^GSPC",
            "NASDAQ 100": "^NDX",
            "DXY (Dolar Endeksi)": "DX-Y.NYB",
            "DAX 40 (Almanya)": "^GDAXI",
            "ETH/USD": "ETH-USD",
            "BTC/USD": "BTC-USD"
        }
        
        fx_secilen = st.selectbox("ANALİZ EDİLECEK ENSTRÜMAN", list(makro_evren.keys()), index=0)
        ticker_sembol = makro_evren[fx_secilen]
        
        fx_periyotlar = {"15 Dakika (Skalping)": "15m", "1 Saat (Gün İçi)": "1h", "1 Gün (Majör Trend)": "1d"}
        secilen_hiz = st.selectbox("ZAMAN DİLİMİ (PERİYOT)", list(fx_periyotlar.keys()), index=1)
        periyot_kod = fx_periyotlar[secilen_hiz]
        
        kutu_bar_boyu = st.slider("Kristal Kutu Bar Genişliği (Matris Ölçüsü)", 30, 200, 90)

    # 🛡️ Veri Çekme Katmanı
    try:
        t_engine = yf.Ticker(ticker_sembol)
        sure_kilit = "1mo" if periyot_kod == "15m" else ("2mo" if periyot_kod == "1h" else "1y")
        df_raw = t_engine.history(period=sure_kilit, interval=periyot_kod)
        
        if df_raw.empty:
            st.error("⚠️ Global sunuculardan veri çekilemedi. Lütfen daha sonra tekrar deneyin.")
        else:
            if isinstance(df_raw.columns, pd.MultiIndex): 
                df_raw.columns = df_raw.columns.get_level_values(0)
            df_raw.columns = [str(c).strip().capitalize() for c in df_raw.columns]

            for col in ['Open', 'High', 'Low', 'Close']:
                if hasattr(df_raw[col], 'columns') or (type(df_raw[col]).__name__ == 'DataFrame'):
                    df_raw[col] = df_raw[col].iloc[:, 0]
            
            df_m = df_raw.tail(kutu_bar_boyu).copy()
            
            son_fiyat = float(df_m['Close'].iloc[-1])
            kutu_tavan = float(df_m['High'].max())
            kutu_taban = float(df_m['Low'].min())
            kutu_merkez = (kutu_tavan + kutu_taban) / 2
            kutu_boyutu = kutu_tavan - kutu_taban
            
            # 📐 1. KATMAN: ATR VOLATİLİTE VE KANAL DARLIK KONTROLÜ
            high_low = df_m['High'] - df_m['Low']
            high_close = np.abs(df_m['High'] - df_m['Close'].shift())
            low_close = np.abs(df_m['Low'] - df_m['Close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            true_range = ranges.max(axis=1)
            atr_val = float(true_range.ewm(span=14, adjust=False).mean().iloc[-1])
            
            # Kanal darlık tespiti
            oransal_genislik = (kutu_boyutu / kutu_merkez) * 100
            is_dar_kanal = oransal_genislik < 1.5
            
            # 📐 2. KATMAN: GANN TAYFI GEOMETRİSİ
            x_idx = np.arange(len(df_m))
            fiyat_adim_katsayisi = kutu_boyutu / len(df_m)
            gann_1x1_son = kutu_taban + (fiyat_adim_katsayisi * 1.0 * x_idx[-1])
            gann_2x1_son = kutu_taban + (fiyat_adim_katsayisi * 2.0 * x_idx[-1])
            
            hiz_skoru = "DENGELİ"
            if son_fiyat > gann_2x1_son: hiz_skoru = "AŞIRI HIZLI BOĞA"
            elif son_fiyat > gann_1x1_son: hiz_skoru = "POZİTİF İVME"
            else: hiz_skoru = "NEGATİF BASKI"

            # 📐 3. KATMAN: RSI VE SİNYAL KOMBİNASYONU
            diff = df_m['Close'].diff()
            rsi_fx = float(100 - (100 / (1 + (diff.clip(lower=0).ewm(com=13, adjust=False).mean() / (-diff.clip(upper=0)).ewm(com=13, adjust=False).mean()))).iloc[-1])

            # Duruma göre dinamik renk ve görsel kalınlık parametreleri
            if son_fiyat >= kutu_tavan:
                if rsi_fx > 52:
                    durum_text = "🚀 KRİSTAL KUTU YUKARI KIRILDI (GÜÇLÜ BOĞA SİNYALİ)"
                    kart_renk = "#2ECC71"
                    kanal_grafik_rengi = "#2ECC71"
                    kanal_kalinligi = 4
                    tp_hedef = son_fiyat + (atr_val * 3.5)
                    sl_stop = kutu_tavan - (atr_val * 1.5)
                else:
                    durum_text = "⚠️ YALANCI KIRILIM RİSKİ (RSI ZAYIF, KUTU ÜSTÜ TUZAK)"
                    kart_renk = "#9B59B6"
                    kanal_grafik_rengi = "#9B59B6"
                    kanal_kalinligi = 2.5
                    tp_hedef = kutu_merkez
                    sl_stop = kutu_tavan + atr_val
            elif son_fiyat <= kutu_taban:
                if rsi_fx < 48:
                    durum_text = "💥 KRİSTAL KUTU AŞAĞI KIRILDI (GÜÇLÜ AYI SİNYALİ)"
                    kart_renk = "#E74C3C"
                    kanal_grafik_rengi = "#E74C3C"
                    kanal_kalinligi = 4
                    tp_hedef = son_fiyat - (atr_val * 3.5)
                    sl_stop = kutu_taban + (atr_val * 1.5)
                else:
                    durum_text = "⚠️ YALANCI KIRILIM RİSKİ (RSI UYUMSUZ, KUTU ALTI TUZAK)"
                    kart_renk = "#9B59B6"
                    kanal_grafik_rengi = "#9B59B6"
                    kanal_kalinligi = 2.5
                    tp_hedef = kutu_merkez
                    sl_stop = kutu_taban - atr_val
            else:
                if is_dar_kanal:
                    durum_text = "⚡ SÜPER DAR KANAL SIKIŞMASI (PATLAMA YAKIN!)"
                    kart_renk = "#F1C40F"
                    kanal_grafik_rengi = "#F39C12"
                    kanal_kalinligi = 4.5
                else:
                    durum_text = "⏳ KUTU İÇİ HACİM SIKIŞMASI (AKÜMÜLASYON SEYRİ)"
                    kart_renk = "#34495E"
                    kanal_grafik_rengi = "#7F8C8D"
                    kanal_kalinligi = 2.5
                tp_hedef = kutu_tavan
                sl_stop = kutu_taban

            # 📊 SİSTEM GÖSTERGE PANELİ
            st.markdown(f"<div style='background-color:{kart_renk};color:white;padding:14px;border-radius:6px;text-align:center;font-weight:bold;font-size:16px;'>{durum_text}</div>", unsafe_allow_html=True)
            st.write("")
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("GÜNCEL FİYAT", f"{son_fiyat:.4f}")
            m2.metric("📦 KUTU TAVANI (DİRENÇ)", f"{kutu_tavan:.4f}")
            m3.metric("📦 KUTU TABANI (DESTEK)", f"{kutu_taban:.4f}")
            m4.metric("📊 KANAL YAPISI", "DAR KANAL (ALARM)" if is_dar_kanal else "NORMAL KORİDOR")

            # 📈 Gelişmiş Plotly Çizim Alanı
            fig_ultra = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.06, row_heights=[0.78, 0.22])
            
            # Mum Grafik Konturu
            fig_ultra.add_trace(go.Candlestick(
                x=df_m.index, open=df_m['Open'], high=df_m['High'], low=df_m['Low'], close=df_m['Close'],
                name=fx_secilen, increasing_line_color='#2ECC71', decreasing_line_color='#E74C3C'
            ), row=1, col=1)
            
            # Kristal Kutu Sınır Hatları
            fig_ultra.add_trace(go.Scatter(x=[df_m.index[0], df_m.index[-1]], y=[kutu_tavan, kutu_tavan], line=dict(color=kanal_grafik_rengi, width=kanal_kalinligi), name="Kutu Direnç Sınırı"), row=1, col=1)
            fig_ultra.add_trace(go.Scatter(x=[df_m.index[0], df_m.index[-1]], y=[kutu_taban, kutu_taban], line=dict(color=kanal_grafik_rengi, width=kanal_kalinligi), name="Kutu Destek Sınırı"), row=1, col=1)
            fig_ultra.add_trace(go.Scatter(x=[df_m.index[0], df_m.index[-1]], y=[kutu_merkez, kutu_merkez], line=dict(color='#7F8C8D', width=1, dash='dot'), name="Merkez Denge Ekseni"), row=1, col=1)

            # Gann Tayfı Geometrisi
            fig_ultra.add_trace(go.Scatter(x=df_m.index, y=kutu_taban + (fiyat_adim_katsayisi * 2.0 * x_idx), line=dict(color='#9B59B6', width=1, dash='dash'), name="Gann 2x1 (İvme)"), row=1, col=1)
            fig_ultra.add_trace(go.Scatter(x=df_m.index, y=kutu_taban + (fiyat_adim_katsayisi * 1.0 * x_idx), line=dict(color='#3498DB', width=1.5), name="Gann 1x1 (Ana Denge)"), row=1, col=1)
            fig_ultra.add_trace(go.Scatter(x=df_m.index, y=kutu_taban + (fiyat_adim_katsayisi * 0.5 * x_idx), line=dict(color='#1ABC9C', width=1, dash='dash'), name="Gann 1x2 (Yavaş)"), row=1, col=1)

            # Duruma Göre Sağ Uca Fırlayan Dinamik Çıkış (TP/SL) Çizgileri
            c_x = [df_m.index[-15], df_m.index[-1]]
            
            if "GÜÇLÜ BOĞA" in durum_text or "GÜÇLÜ AYI" in durum_text:
                fig_ultra.add_trace(go.Scatter(x=c_x, y=[tp_hedef, tp_hedef], line=dict(color='#2ECC71', width=3.5, dash='solid'), name="Hedef (TP)"), row=1, col=1)
                fig_ultra.add_trace(go.Scatter(x=c_x, y=[sl_stop, sl_stop], line=dict(color='#D50000', width=3.5, dash='solid'), name="Zarar Kes (SL)"), row=1, col=1)
            elif "YALANCI KIRILIM" in durum_text:
                fig_ultra.add_trace(go.Scatter(x=c_x, y=[tp_hedef, tp_hedef], line=dict(color='#9B59B6', width=2.5, dash='dot'), name="Tuzak Dönüş Hedefi"), row=1, col=1)
                fig_ultra.add_trace(go.Scatter(x=c_x, y=[sl_stop, sl_stop], line=dict(color='#7F8C8D', width=2.5, dash='dash'), name="Tuzak Risk Limiti"), row=1, col=1)
            else:
                fig_ultra.add_trace(go.Scatter(x=c_x, y=[kutu_tavan, kutu_tavan], line=dict(color='#E74C3C', width=1.5, dash='dot'), name="Yukarı Tetik Hattı"), row=1, col=1)
                fig_ultra.add_trace(go.Scatter(x=c_x, y=[kutu_taban, kutu_taban], line=dict(color='#2ECC71', width=1.5, dash='dot'), name="Aşağı Tetik Hattı"), row=1, col=1)

            # Alt İndikatör Paneli (Hatasız Sabit RSI)
            fig_ultra.add_trace(go.Scatter(x=df_m.index, y=[rsi_fx]*len(df_m), line=dict(color='#16A085', width=1.5), name="RSI (14)"), row=2, col=1)
            fig_ultra.add_shape(type="line", x0=df_m.index[0], y0=50, x1=df_m.index[-1], y1=50, line=dict(color="gray", dash="dash"), row=2, col=1)
            
            # =================================================================================
            # 🔓 GRAFİĞİ SERBEST BIRAKAN HASSAS YAPILANDIRMA PANELİ
            # =================================================================================
            fig_ultra.update_layout(
                height=650,
                template="plotly_white",
                xaxis_rangeslider_visible=False,
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(orientation="h", y=1.05, x=0),
                
                dragmode="pan",  # Sürükleme modunu doğrudan el ile tutmaya ayarladık
                
                # Eksen kilitlerini kaldırıyoruz (Yukarı, aşağı, sağa, sola serbest salınım)
                xaxis=dict(fixedrange=False),
                yaxis=dict(fixedrange=False),
                xaxis2=dict(fixedrange=False),
                yaxis2=dict(fixedrange=False)
            )
            
            st.plotly_chart(
                fig_ultra, 
                use_container_width=True, 
                config={
                    'scrollZoom': True,      # Fare tekerleği veya çift parmakla serbest zoom yapar
                    'displayModeBar': True,  # Üst panel kontrol çubuğunu açar
                    'modeBarButtonsToRemove': ['select2d', 'lasso2d'] # Arayüzü sadeleştirir
                }
            )

            # 🎯 STRATEJİK HEDEF MATRİSİ CARD ALANI
            st.markdown("### 🏹 QUANT STRATEJİ KARTI")
            s1, s2, s3 = st.columns(3)
            
            if "GÜÇLÜ BOĞA" in durum_text or "GÜÇLÜ AYI" in durum_text:
                s1.success(f"🎯 **Kâr Al (TP) Seviyesi:** {tp_hedef:.4f}")
                s2.error(f"🛑 **Zarar Kes (SL) Seviyesi:** {sl_stop:.4f}")
                s3.info(f"⚖️ **Trend İvme Skoru:** {hiz_skoru}")
            elif "YALANCI KIRILIM" in durum_text:
                s1.warning("⚠️ İşleme Girme! (Tuzak Aktif)")
                s2.info(f"🔄 Kutu İçi Geri Çekilme Hedefi: {tp_hedef:.4f}")
                s3.write(f"RSI Seviyesi: {rsi_fx:.1f}")
            else:
                s1.info(f"⚡ Üst Sınır Geçilirse (AL): {kutu_tavan:.4f}")
                s2.info(f"⚡ Alt Sınır Patlarsa (SAT): {kutu_taban:.4f}")
                s3.write(f"📦 Kutu Genişlik Oranı: %{oransal_genislik:.2f}")
                
    except Exception as e:
        st.warning("Veriler işlenirken anlık bir senkronizasyon gecikmesi oldu. Grafik güncelleniyor...")
