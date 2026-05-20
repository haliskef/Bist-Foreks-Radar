import streamlit as st
from streamlit_autorefresh import st_autorefresh
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import time
import os
import threading

# ==========================================
# 1. SAYFA AYARLARI VE ARAYÜZ TASARIMI
# ==========================================
st.set_page_config(layout="wide", page_title="BIST & KÜRESEL HİBRİT KOMUTA MERKEZİ")

# UI/UX OPTİMİZASYONU (Açık Tema Korundu)
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
        "Forex & Küresel Piyasalar (Çift Yönlü)"
    ])
    st.markdown("---")

# KÜRESEL ENSTRÜMAN SÖZLÜĞÜ
forex_assets = {
    "ONS ALTIN": "GC=F",
    "ONS GÜMÜŞ": "SI=F",
    "ONS BAKIR" : "HG=F",
    "ONS PALADYUM": "PA=F",
    "ONS PLATİN": "PL=F",
    "BRENT PETROL": "BZ=F",
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

# TELEGRAM ENTEGRASYON BİLGİLERİ
TELEGRAM_BOT_TOKEN = "8817119197:AAHcHADLXZ7DbLgJp7yskg94QO0Q6jJd85s"
TELEGRAM_CHAT_ID = "1338802399"

def telegram_mesaj_gonder(mesaj):
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        try:
            import requests
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mesaj, "parse_mode": "Markdown"}
            requests.post(url, json=payload, timeout=5)
        except:
            pass

# OTONOM RADAR LİSTESİ (Lazer Modunda Arka Planda Çalışır)
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

# =================================================================================
# ÇEKİRDEK 1: LAZER MODU
# =================================================================================
if calisma_modu == "Lazer (Detaylı Analiz & Strateji)":
    st_autorefresh(interval=45000, limit=500, key="lazer_canli_guncelleme_fixed")
    
    with st.sidebar:
        st.markdown("### ⚙️ HİSSE PARAMETRELERİ")
        hisse = st.text_input("HİSSE KODU", "THYAO.IS").upper()
        zaman_sozlugu = {"15 Dikika": "15m", "1 Saat": "1h", "1 Gün": "1d"}
        secilen_int = st.selectbox("VERİ SIKLIĞI", list(zaman_sozlugu.keys()), index=2)
        view_period = st.selectbox("GÖRÜNÜM ARALIĞI", ["1 Ay", "3 Ay", "6 Ay", "1 Yıl", "Tümü"], index=2)

    if "otonom_radar_aktif" not in st.session_state:
        st.session_state.otonom_radar_aktif = False
    if "otonom_son_gonderilenler" not in st.session_state:
        st.session_state.otonom_son_gonderilenler = {} 

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

                    if isinstance(fk_o, float) and fk_o > 0 and fk_o < 15: 
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
                        son_atim_zamani = st.session_state.otonom_son_gonderilenler.get(hisse_temiz, 0.0)
                        if (simdi - son_atim_zamani) > 3600.0:
                            st.session_state.otonom_son_gonderilenler[hisse_temiz] = simdi
                            gerekce_metni = "\n".join(o_maddeler)
                            radar_mesaj = (
                                f"🛰️ *BIST 100 OTONOM RADAR SİNYALİ*\n\n"
                                f"**Hisse:** #{hisse_temiz}\n"
                                f"**Anlık Fiyat:** `{fiyat_o:.2f} TL`\n"
                                f"**Yapay Zeka Skoru:** `{o_puan} / 10` 🔥\n\n"
                                f"**🔍 Tespit Edilen Güçlü Gerekçeler:**\n{gerekce_metni}\n"
                            )
                            telegram_mesaj_gonder(radar_mesaj)
                    time.sleep(3.5)
                except:
                    time.sleep(2)
            time.sleep(10)

    if not st.session_state.otonom_radar_aktif:
        t = threading.Thread(target=saf_arka_plan_tarayici, daemon=True)
        t.start()
        st.session_state.otonom_radar_aktif = True

    state_sinyal_key = f"bist_hybrid_state_{hisse}"
    state_fiyat_key = f"bist_hybrid_price_{hisse}"
    state_zaman_key = f"bist_hybrid_time_{hisse}"
    
    if state_sinyal_key not in st.session_state: st.session_state[state_sinyal_key] = "NÖTR (İZLE)"
    if state_fiyat_key not in st.session_state: st.session_state[state_fiyat_key] = 0.0
    if state_zaman_key not in st.session_state: st.session_state[state_zaman_key] = 0.0
        
    @st.cache_data(ttl=45)
    def get_full_data(kod, interval):
        try:
            ticker = yf.Ticker(kod)
            p = "2y" if interval in ["1h", "1d"] else "1mo"
            data = ticker.history(period=p, interval=interval)
            if data.empty or len(data) < 5:
                data = ticker.history(period="2y", interval="1d")
            info = ticker.info
            if data.empty: return pd.DataFrame(), {}
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
        except: return pd.DataFrame(), {}

    @st.cache_data(ttl=3600)
    def otonom_sektor_hesapla(hisse_kodu):
        sektorler = {
            "HAVACILIK": ["THYAO.IS", "PGSUS.IS", "TAVHL.IS", "CLEBI.IS", "DOCO.IS"],
            "BANKACILIK": ["AKBNK.IS", "GARAN.IS", "ISCTR.IS", "YKBNK.IS", "HALKB.IS", "VAKBN.IS", "ALBRK.IS", "SKBNK.IS", "TSKB.IS"],
            "OTOMOTİV & YAN SANAYİ": ["FROTO.IS", "TOASO.IS", "DOAS.IS", "KARSN.IS", "ASUZU.IS", "TTRAK.IS", "OTKAR.IS", "BRISA.IS", "EGEEN.IS"],
            "ENERJİ & GAZ": ["ENJSA.IS", "ASTOR.IS", "AKSEN.IS", "GWIND.IS", "SMRTG.IS", "ALFAS.IS", "CWENE.IS", "EUPWR.IS", "ZOREN.IS", "ODAS.IS"],
            "HOLDİNG & YATIRIM": ["KCHOL.IS", "SAHOL.IS", "ALARK.IS", "DOHOL.IS", "AGHOL.IS"],
            "DEMİR-ÇELİK": ["EREGL.IS", "KRDMD.IS", "ISDMR.IS", "KCAER.IS", "BRSAN.IS"],
            "PERAKENDE & TİCARET": ["BIMAS.IS", "MGROS.IS", "SOKM.IS", "MAVI.IS"],
            "ÇİMENTO & CAM & SERAMİK": ["AKCNS.IS", "CIMSA.IS", "OYAKC.IS", "SISE.IS", "KONYA.IS"],
            "TELEKOMÜNİKASYON": ["TCELL.IS", "TTKOM.IS"],
            "GIDA & İÇECEK": ["CCOLA.IS", "AEFES.IS", "ULKER.IS", "TABGD.IS", "YYLGD.IS"],
            "TEKNOLOJİ & BİLİŞİM": ["HKTM.IS", "KONTR.IS", "MIATK.IS", "PENTA.IS"],
            "SAVUNMA SANAYİ": ["ASELS.IS", "SDTTR.IS"],
            "KİMYA & PETROKİMYA & GÜBRE": ["AKSA.IS", "GUBRF.IS", "HEKTS.IS", "PETKM.IS", "SASA.IS", "TUPRS.IS"]
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

    df_all, info_data = get_full_data(hisse, zaman_sozlugu[secilen_int])

    if df_all.empty or 'Close' not in df_all.columns or len(df_all) < 5:
        st.error("⚠️ Seçilen hisse için veri çekilemedi. Lütfen hisse kodunun doğru yazıldığından emin olun (Örn: THYAO.IS).")
    else:
        df = df_all.copy()
        df['EMA7'] = df['Close'].ewm(span=7, adjust=False).mean()
        df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
        df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['EMA100'] = df['Close'].ewm(span=100, adjust=False).mean()
        df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
        
        delta = df['Close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        df['RSI'] = 100 - (100 / (1 + (gain.ewm(com=13, adjust=False).mean() / loss.ewm(com=13, adjust=False).mean())))
        
        df['MACD_12_26_9'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
        df['MACDs_12_26_9'] = df['MACD_12_26_9'].ewm(span=9, adjust=False).mean()
        df['MACDh_12_26_9'] = df['MACD_12_26_9'] - df['MACDs_12_26_9']
        
        if view_period == "1 Ay": df_plot = df.tail(30).copy()
        elif view_period == "3 Ay": df_plot = df.tail(90).copy()
        elif view_period == "6 Ay": df_plot = df.tail(180).copy()
        elif view_period == "1 Yıl": df_plot = df.tail(365).copy()
        else: df_plot = df.copy()

        son_fiyat = df['Close'].iloc[-1].item()
        rsi_val = df['RSI'].iloc[-1].item()

        try:
            bugun = df_all.index[-1].date()
            gun_verisi = df_all[df_all.index.date == bugun]
            if not gun_verisi.empty:
                gun_acilisi = gun_verisi['Open'].iloc[0].item()
            else:
                gun_acilisi = df_all['Open'].iloc[-1].item()
            onceki_gunler = df_all[df_all.index.date < bugun]
            if not onceki_gunler.empty:
                onceki_kapanis = onceki_gunler['Close'].iloc[-1].item()
                gunluk_yuzde = ((son_fiyat - onceki_kapanis) / onceki_kapanis) * 100
                delta_str = f"{gunluk_yuzde:.2f}%"
            else: delta_str = None
        except:
            gun_acilisi = df_all['Open'].iloc[-1].item()
            delta_str = None

        max_price = df_plot['High'].max()
        min_price = df_plot['Low'].min()
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
            son_ust = df_plot['Ust_Trend'].iloc[-1]
            son_alt = df_plot['Alt_Trend'].iloc[-1]
        else:
            df_plot['Orta_Trend'] = df_plot['Close']
            df_plot['Ust_Trend'] = df_plot['Close']
            df_plot['Alt_Trend'] = df_plot['Close']
            son_ust = son_fiyat
            son_alt = son_fiyat
            slope = 0

        if son_fiyat > son_ust:
            kanal_durumu = f"🚀 DİKKAT: Kanalı YUKARI Kırdı! ({son_ust:.2f} Direnci Aşıldı)"
            kanal_renk = "green"
        elif son_fiyat < son_alt:
            kanal_durumu = f"💥 DİKKAT: Kanalı AŞAĞI Kırdı! ({son_alt:.2f} Desteği Çöktü)"
            kanal_renk = "red"
        elif slope > 0:
            kanal_durumu = f"📈 HİSSE YÜKSELEN TREND KANALINDA İLERLİYOR (Pozitif)"
            kanal_renk = "green"
        else:
            kanal_durumu = f"📉 HİSSE DÜŞEN TREND KANALINDA İLERLİYOR (Negatif)"
            kanal_renk = "orange"

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name="Fiyat", increasing_line_color='#00C853', increasing_fillcolor='#00C853', decreasing_line_color='#D50000', decreasing_fillcolor='#D50000'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['Ust_Trend'], name="Kanal Üst", line=dict(color='rgba(255, 152, 0, 0.8)', width=2, dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['Alt_Trend'], name="Kanal Alt", line=dict(color='rgba(255, 152, 0, 0.8)', width=2, dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['Orta_Trend'], name="Trend Ekseni", line=dict(color='#000000', width=2.5, dash='dashdot')), row=1, col=1)

        for isim, deger in fib_seviyeleri.items():
            fig.add_hline(y=deger, line_dash="dot", line_color="gray", opacity=0.5, row=1, col=1)
        
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA21'], name="EMA 21", line=dict(color='#1f77b4', width=2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA50'], name="EMA 50", line=dict(color='#FF9800', width=1.5, dash='dash')), row=1, col=1)
        
        if 'MACDh_12_26_9' in df_plot.columns:
            colors = ['#00C853' if val >= 0 else '#D50000' for val in df_plot['MACDh_12_26_9']]
            fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['MACDh_12_26_9'], name="MACD", marker_color=colors), row=2, col=1)
        
        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])], showspikes=True, spikemode="across", spikedash="dot")
        fig.update_layout(height=600, template="plotly_white", xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

        if kanal_renk == "green": st.success(kanal_durumu)
        elif kanal_renk == "red": st.error(kanal_durumu)
        else: st.warning(kanal_durumu)

        fk_val = info_data.get('trailingPE', None)
        pddd_val = info_data.get('priceToBook', None)
        favok_marji = info_data.get('ebitdaMargins', None)
        roe_val = info_data.get('returnOnEquity', None)

        oto_sektor_fk, sektor_adi = otonom_sektor_hesapla(hisse)

        st.markdown("### 📋 MALİ RÖNTGEN")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("F/K", f"{fk_val:.2f}" if isinstance(fk_val, float) else "N/A")
        k2.metric("PD/DD", f"{pddd_val:.2f}" if isinstance(pddd_val, float) else "N/A")
        k3.metric("FAVÖK Marjı", f"%{round(favok_marji*100, 2)}" if favok_marji else "N/A")
        k4.metric("ROE (Özsermaye Kâr.)", f"%{round(roe_val*100, 2)}" if roe_val else "N/A")

        ai_puan = 0.0
        ai_rapor_maddeleri = []

        if isinstance(fk_val, float) and fk_val > 0:
            if oto_sektor_fk and fk_val < oto_sektor_fk:
                ai_puan += 1.5
                ai_rapor_maddeleri.append(f"📊 **F/K Oranı Olumlu:** Hisse F/K'sı ({fk_val:.2f}), rakip {sektor_adi} sektör ortalamasından ({oto_sektor_fk}) daha iskontolu.")
            elif fk_val < 15:
                ai_puan += 1.0
                ai_rapor_maddeleri.append(f"📊 **F/K Oranı Makul:** Sektör verisi eksik fakat {fk_val:.2f} genel piyasa çarpanlarına göre makul.")

        if isinstance(pddd_val, float) and 0 < pddd_val < 3.5:
            ai_puan += 1.0
            ai_rapor_maddeleri.append(f"📑 **Defter Değeri Dengeli:** PD/DD oranı {pddd_val:.2f} ile özsermayeye göre güvenli bölgede.")

        if roe_val and roe_val > 0.15:
            ai_puan += 1.0
            ai_rapor_maddeleri.append(f"💰 **Yeterli Kârlılık (ROE):** %{roe_val*100:.2f} kârlılık rasyosu enflasyon/faiz dengesinde makul.")

        if favok_marji and favok_marji > 0.15:
            ai_puan += 1.0
            ai_rapor_maddeleri.append(f"🏭 **Güçlü Operasyonel Kâr:** FAVÖK marjı %{favok_marji*100:.2f} ile ana faaliyet alanında güçlü nakit üretiyor.")

        if 30 <= rsi_val <= 45:
            ai_puan += 2.0
            ai_rapor_maddeleri.append(f"🎯 **RSI Toplama Alanı:** RSI değeri ({rsi_val:.2f}) teknik olarak talebin canlanabileceği dip destek bölgesinde.")
        elif rsi_val < 30:
            ai_puan += 1.5
            ai_rapor_maddeleri.append(f"🔥 **Aşırı Satım Tepkisi:** RSI ({rsi_val:.2f}) aşırı satım bölgesinde, fiyatta yukarı yönlü tepki beklentisi yüksek.")

        if son_fiyat > df['EMA50'].iloc[-1]:
            ai_puan += 1.5
            ai_rapor_maddeleri.append("📈 **EMA50 Trend Gücü Üstün:** Fiyatın 50 günlük hareketli ortalamanın üzerinde olması yönün yukarı olduğunu teyit ediyor.")

        ai_puan = min(10.0, max(0.0, round(ai_puan, 1)))

        st.markdown(f"""
        <div class="ai-score-box">
            <h2>🧠 HİBRİT YAPAY ZEKA SKORU</h2>
            <h1>{ai_puan} / 10</h1>
            <div style="background-color: #444; width: 100%; height: 14px; border-radius: 7px; margin-bottom: 15px; overflow: hidden;">
                <div style="width: {int(ai_puan * 10)}%; background: linear-gradient(90deg, #FF8C00 0%, #FFD700 100%); height: 100%; border-radius: 7px;"></div>
            </div>
        """, unsafe_allow_html=True)
        for m in ai_rapor_maddeleri:
            st.markdown(f"<span style='color: #FFFFFF !important;'>{m}</span>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("## 🌍 ANA PİYASA DURUMU (BIST 100 & 30)")

        @st.cache_data(ttl=60)
        def get_index_data_safe(symbol):
            try:
                idx_ticker = yf.Ticker(symbol)
                data = idx_ticker.history(period="6mo", interval="1d")
                if data.empty or len(data) < 5: return pd.DataFrame()
                if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
                data.columns = [str(c).strip().capitalize() for c in data.columns]
                data['EMA21'] = data['Close'].ewm(span=21, adjust=False).mean()
                data['EMA50'] = data['Close'].ewm(span=50, adjust=False).mean()
                idx_delta = data['Close'].diff()
                idx_gain = idx_delta.clip(lower=0)
                idx_loss = -idx_delta.clip(upper=0)
                data['RSI'] = 100 - (100 / (1 + (idx_gain.ewm(com=13, adjust=False).mean() / idx_loss.ewm(com=13, adjust=False).mean())))
                return data
            except: return pd.DataFrame()

        def endeks_yorumla(df_idx):
            if df_idx.empty or 'Close' not in df_idx.columns: 
                return "Piyasa verisi okunamıyor. Sistem hisse analiz modunda çalışmaya devam ediyor.", "orange"
            son_kapanis = float(df_idx['Close'].iloc[-1])
            e21 = float(df_idx['EMA21'].iloc[-1])
            e50 = float(df_idx['EMA50'].iloc[-1])
            if son_kapanis > e21 and e21 > e50: 
                return "🚀 GÜÇLÜ BOĞA PİYASASI: Endeks ana ortalamaların üzerinde.", "green"
            return "⏳ KONSOLİDASYON / KARARSIZ BÖLGE: Ortalamalar yatay seyirde.", "orange"

        idx_col1, idx_col2 = st.columns(2)
        with idx_col1:
            st.subheader("BIST 100 (XU100)")
            df_x100 = get_index_data_safe("^XU100")
            if not df_x100.empty:
                st.line_chart(df_x100['Close'], use_container_width=True)
                yorum_100, renk_100 = endeks_yorumla(df_x100)
                if renk_100 == "green": st.success(yorum_100)
                else: st.warning(yorum_100)
        
        with idx_col2:
            st.subheader("BIST 30 (XU030)")
            df_x030 = get_index_data_safe("^XU030")
            if not df_x030.empty:
                st.line_chart(df_x030['Close'], use_container_width=True)
                yorum_30, renk_30 = endeks_yorumla(df_x030)
                if renk_30 == "green": st.success(yorum_30)
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
        if anlik_durum_yuzde > 0: 
            c2.success(f"📈 ANLIK DURUM:\n### +%{anlik_durum_yuzde:.2f}")
        else: 
            c2.error(f"📉 ANLIK DURUM:\n### %{anlik_durum_yuzde:.2f}")
        c3.error(f"🛑 STOP FİYATI:\n### {stop_fiyat:.2f} TL")

# =================================================================================
# ÇEKİRDEK 2: FULL HİBRİT RADAR
# =================================================================================
elif calisma_modu == "Radar (BIST 100 Full Hibrit Tarama)":
    st.markdown("## 📡 BIST 100 DERİN HİBRİT TARAMA (TEKNİK + TEMEL)")
    if 'hibrit_tablo_full' not in st.session_state:
        try:
            st.session_state.hibrit_tablo_full = pd.read_csv("son_tarama_kaydi.csv")
        except FileNotFoundError:
            st.session_state.hibrit_tablo_full = pd.DataFrame()

    bist100_tam_liste = [
        "AEFES.IS", "AGHOL.IS", "AKBNK.IS", "AKCNS.IS", "AKFGY.IS", "AKSA.IS", "AKSEN.IS", "ALARK.IS", "ALBRK.IS", "ALFAS.IS", "ARCLK.IS", "ASELS.IS", "ASTOR.IS", "ASUZU.IS", "AYDEM.IS", "AYGAZ.IS", "BAGFS.IS", "BERA.IS", "BIENY.IS", "BIMAS.IS", "BRISA.IS", "BRSAN.IS", "BUCIM.IS", "CANTE.IS", "CCOLA.IS", "CIMSA.IS", "CWENE.IS", "DOAS.IS", "DOHOL.IS", "EGEEN.IS", "ECILC.IS", "EKGYO.IS", "ENERY.IS", "ENJSA.IS", "ENKAI.IS", "EREGL.IS", "EUREN.IS", "EUPWR.IS", "FROTO.IS", "GARAN.IS", "GENIL.IS", "GESAN.IS", "GLYHO.IS", "GUBRF.IS", "GWIND.IS"
    ]

    if st.button("🚀 BIST 100 CANLI RADARI BAŞLAT"):
        sonuclar = []
        ilerleme = st.progress(0)
        durum_m = st.empty()
        
        for i, kod in enumerate(bist100_tam_liste):
            durum_m.text(f"🔍 {kod} Analiz Ediliyor... ({i+1}/{len(bist100_tam_liste)})")
            try:
                tk = yf.Ticker(kod)
                df_h = tk.history(period="3mo", interval="1d")
                if df_h.empty or len(df_h) < 10: continue
                if isinstance(df_h.columns, pd.MultiIndex): df_h.columns = df_h.columns.get_level_values(0)
                df_h.columns = [str(c).strip().capitalize() for c in df_h.columns]

                inf = tk.info
                fiyat = df_h['Close'].iloc[-1].item()
                fk = inf.get('trailingPE', 100)
                pddd = inf.get('priceToBook', 100)
                roe = inf.get('returnOnEquity', None)
                
                delta_h = df_h['Close'].diff()
                gain_h = delta_h.clip(lower=0)
                loss_h = -delta_h.clip(upper=0)
                rsi = 100 - (100 / (1 + (gain_h.ewm(com=13, adjust=False).mean() / loss_h.ewm(com=13, adjust=False).mean()))).iloc[-1].item()
                
                skor = 0
                if fk < 15: skor += 1
                if pddd < 3.5: skor += 1
                if rsi < 45: skor += 1
                if roe and roe > 0.20: skor += 1
                
                sonuclar.append({
                    "Hisse": kod.replace(".IS", ""),
                    "Fiyat (TL)": round(fiyat, 2),
                    "F/K": round(fk, 2) if fk != 100 else "N/A",
                    "PD/DD": round(pddd, 2) if pddd != 100 else "N/A",
                    "ROE (%)": round(roe*100, 2) if roe else "N/A",
                    "RSI": round(rsi, 2),
                    "Hibrit Skor": skor,
                    "Sistem Notu": "👑 ŞAMPİYON" if skor >= 4 else ("🟢 GÜÇLÜ" if skor == 3 else ("🟡 MAKUL" if skor == 2 else "⚪ İZLE"))
                })
                time.sleep(0.1)
            except:
                pass
            ilerleme.progress((i + 1) / len(bist100_tam_liste))
            
        if sonuclar:
            df_sonuc = pd.DataFrame(sonuclar)
            if "Hibrit Skor" in df_sonuc.columns:
                df_sonuc = df_sonuc.sort_values(by="Hibrit Skor", ascending=False).reset_index(drop=True)
            else:
                df_sonuc = df_sonuc.reset_index(drop=True)
            st.session_state.hibrit_tablo_full = df_sonuc
            df_sonuc.to_csv("son_tarama_kaydi.csv", index=False)
            durum_m.success("✅ Kaydedildi!")
        else:
            durum_m.error("🚨 Veri çekilemedi. Bağlantıyı kontrol edin.")

    if not st.session_state.hibrit_tablo_full.empty:
        def renk_motoru(val):
            if val == "👑 ŞAMPİYON": return 'background-color: #FFD700; color: black; font-weight: bold;'
            if val == "🟢 GÜÇLÜ": return 'background-color: #C8E6C9; color: black; font-weight: bold;'
            return ''
        styled_df = st.session_state.hibrit_tablo_full.style.map(renk_motoru, subset=['Sistem Notu'])
        st.dataframe(styled_df, use_container_width=True, height=800)

# =================================================================================
# ÇEKİRDEK 3: FOREX & KÜRESEL PİYASALAR (Tamamen Onarılan Bölüm)
# =================================================================================
elif calisma_modu == "Forex & Küresel Piyasalar (Çift Yönlü)":
    st_autorefresh(interval=60000, key="global_forex_multi_scan_v11_protected")
    st.markdown("## 🌐 ÇİFT YÖNLÜ OTONOM FOREX KOMUTA MERKEZİ (7/24 ARKA PLAN TARAYICISI)")

    if st.button("🧪 Bağlantı Hattını Test Et"):
        try:
            import requests
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {"chat_id": TELEGRAM_CHAT_ID, "text": "🎯 *SİSTEM TESTİ BAŞARILI!*\n\nÇoklu tarama modunda Telegram hattınız aktiftir.", "parse_mode": "Markdown"}
            response = requests.post(url, json=payload, timeout=5)
            if response.status_code == 200: 
                st.success("🎯 Harika! Mesaj başarıyla gönderildi.")
            else: 
                st.error(f"❌ Telegram Hata: {response.text}")
        except Exception as e:
            st.error(f"🚨 Bağlantı Hatası: {e}")

    st.info("🔄 Sistem menüden bağımsız olarak tüm listeyi tarar, kırılım anında sinyal gönderir.")
    secilen_forex_adi = st.selectbox("Ekranda Detaylı İncelemek İstediğiniz Küresel Enstrüman:", list(forex_assets.keys()))

    # Her enstrümanın kendi döngüsü ve FX Ekran Yapısı
    for asset_adi, asset_ticker in forex_assets.items():
        state_sinyal_key = f"fx_state_yon_{asset_adi}"
        state_fiyat_key = f"fx_lock_price_{asset_adi}"
        
        if state_sinyal_key not in st.session_state: st.session_state[state_sinyal_key] = "NÖTR (İZLE)"
        if state_fiyat_key not in st.session_state: st.session_state[state_fiyat_key] = 0.0
        
        try:
            df_fx = yf.download(tickers=asset_ticker, period="1mo", interval="1h", progress=False)
        except:
            continue
            
        if not df_fx.empty and len(df_fx) > 25:
            if isinstance(df_fx.columns, pd.MultiIndex): df_fx.columns = df_fx.columns.get_level_values(0)
            df_fx.columns = [str(c).strip().capitalize() for c in df_fx.columns]
            
            df_fx['box_ust'] = df_fx['High'].rolling(window=20).max()
            df_fx['box_alt'] = df_fx['Low'].rolling(window=20).min()
            df_fx['EMA21'] = df_fx['Close'].ewm(span=21, adjust=False).mean()
            df_fx['EMA50'] = df_fx['Close'].ewm(span=50, adjust=False).mean()
            
            fx_delta = df_fx['Close'].diff()
            fx_gain = fx_delta.clip(lower=0)
            fx_loss = -fx_delta.clip(upper=0)
            df_fx['RSI'] = 100 - (100 / (1 + (fx_gain.ewm(com=13, adjust=False).mean() / fx_loss.ewm(com=13, adjust=False).mean())))
            
            high_prices = df_fx['High'].values
            low_prices = df_fx['Low'].values
            close_prices = df_fx['Close'].values
            atr_list = [0.0]
            for idx in range(1, len(df_fx)):
                h_l = high_prices[idx] - low_prices[idx]
                h_pc = abs(high_prices[idx] - close_prices[idx-1])
                l_pc = abs(low_prices[idx] - close_prices[idx-1])
                atr_list.append(max(h_l, h_pc, l_pc))
            df_fx['ATR'] = pd.Series(atr_list, index=df_fx.index).ewm(span=14, adjust=False).mean()

            son_mum = df_fx.iloc[-1]
            onceki_mum = df_fx.iloc[-2]
            son_fiyat = float(son_mum['Close'])
            b_ust = float(onceki_mum['box_ust'])
            b_alt = float(onceki_mum['box_alt'])
            ema21 = float(son_mum['EMA21'])
            ema50 = float(son_mum['EMA50'])
            rsi_val = float(son_mum['RSI'])
            atr_val = float(son_mum['ATR'])

            # Mum Formasyonları Kontrolleri
            is_bullish_pin = (son_mum['High'] - max(son_mum['Open'], son_mum['Close'])) < (abs(son_mum['Open'] - son_mum['Close']) * 0.2) and (min(son_mum['Open'], son_mum['Close']) - son_mum['Low']) > (abs(son_mum['Open'] - son_mum['Close']) * 2)
            is_bearish_pin = (son_mum['High'] - max(son_mum['Open'], son_mum['Close'])) > (abs(son_mum['Open'] - son_mum['Close']) * 2) and (min(son_mum['Open'], son_mum['Close']) - son_mum['Low']) < (abs(son_mum['Open'] - son_mum['Close']) * 0.2)
            is_bullish_engulfing = (onceki_mum['Close'] < onceki_mum['Open']) and (son_mum['Close'] > son_mum['Open']) and (son_mum['Close'] > onceki_mum['Open'])
            is_bearish_engulfing = (onceki_mum['Close'] > onceki_mum['Open']) and (son_mum['Close'] < son_mum['Open']) and (son_mum['Close'] < onceki_mum['Open'])
            
            son_ekstrem_zirve = df_fx['High'].tail(15).iloc[:-1].max()
            son_ekstrem_dip = df_fx['Low'].tail(15).iloc[:-1].min()
            is_msb_bullish = son_fiyat > son_ekstrem_zirve
            is_msb_bearish = son_fiyat < son_ekstrem_dip

            long_skor = 0.0
            short_skor = 0.0
            nedenler = []

            if son_fiyat > b_ust:
                long_skor += 3.5
                nedenler.append("🟩 KRİSTAL BOX: Üst band yukarı yönlü kırıldı (Long +3.5)")
            elif son_fiyat < b_alt:
                short_skor += 3.5
                nedenler.append("🟥 KRİSTAL BOX: Alt band aşağı yönlü kırıldı (Short +3.5)")
            else:
                long_skor += 0.5; short_skor += 0.5
                nedenler.append("🟨 KRİSTAL BOX: Fiyat kutu içinde konsolide oluyor (Nötr +0.5)")

            if son_fiyat > ema21 and ema21 > ema50:
                long_skor += 3.0
                nedenler.append("🟩 GANN/TREND: EMA'lar boğa diziliminde ve fiyat üstünde (Long +3.0)")
            elif son_fiyat < ema21 and ema21 < ema50:
                short_skor += 3.0
                nedenler.append("🟥 GANN/TREND: EMA'lar ayı diziliminde ve fiyat altında (Short +3.0)")
            else:
                nedenler.append("🟨 GANN/TREND: Hareketli ortalamalar kararsız bölgede")

            if 50 < rsi_val < 70: long_skor += 1.5
            elif 30 < rsi_val <= 50: short_skor += 1.5
            elif rsi_val >= 70: short_skor += 1.0
            elif rsi_val <= 30: long_skor += 1.0

            if is_bullish_pin: long_skor += 1.5; nedenler.append("🟩 MUMLAR: Bullish Pin Bar (Çekiç) desteği yakalandı (+1.5 Long)")
            if is_bearish_pin: short_skor += 1.5; nedenler.append("🟥 MUMLAR: Bearish Pin Bar (Ters Çekiç) direnci yakalandı (+1.5 Short)")
            if is_bullish_engulfing: long_skor += 2.0; nedenler.append("🟩 MUMLAR: Yutan Boğa formasyonu oluştu (+2.0 Long)")
            if is_bearish_engulfing: short_skor += 2.0; nedenler.append("🟥 MUMLAR: Yutan Ayı formasyonu oluştu (+2.0 Short)")
            if is_msb_bullish: long_skor += 1.0; nedenler.append("🟩 YAPI: Market Yapısı Yukarı Kırıldı (MSB Bullish +1.0)")
            if is_msb_bearish: short_skor += 1.0; nedenler.append("🟥 YAPI: Market Yapısı Aşağı Kırıldı (MSB Bearish +1.0)")

            anlik_algoritma_yonu = "NÖTR (İZLE)"
            if long_skor >= 6.5 and long_skor > short_skor: anlik_algoritma_yonu = "LONG (YUKARI)"
            elif short_skor >= 6.5 and short_skor > long_skor: anlik_algoritma_yonu = "SHORT (AŞAĞI)"

            eski_yon = st.session_state[state_sinyal_key]
            if anlik_algoritma_yonu != grandfather_yon := eski_yon and anlik_algoritma_yonu != "NÖTR (İZLE)":
                st.session_state[state_sinyal_key] = anlik_algoritma_yonu
                st.session_state[state_fiyat_key] = son_fiyat
                
                hedef_tp = son_fiyat + (atr_val * 3.0) if anlik_algoritma_yonu == "LONG (YUKARI)" else son_fiyat - (atr_val * 3.0)
                risk_sl = son_fiyat - (atr_val * 1.5) if anlik_algoritma_yonu == "LONG (YUKARI)" else son_fiyat + (atr_val * 1.5)
                skor_val = long_skor if anlik_algoritma_yonu == "LONG (YUKARI)" else short_skor
                emoji = "🚀" if anlik_algoritma_yonu == "LONG (YUKARI)" else "💥"
                
                mesaj_metni = (
                    f"{emoji} *OTONOM KIRILIM BİLDİRİMİ*\n\n"
                    f"**Enstrüman:** {asset_adi}\n"
                    f"**Strateji Yönü:** {anlik_algoritma_yonu}\n"
                    f"**Giriş Seviyesi:** `{son_fiyat:.4f}`\n"
                    f"**Hedef (TP):** `{hedef_tp:.4f}`\n"
                    f"**Zarar Kes (SL):** `{risk_sl:.4f}`\n"
                    f"**Sistem Güven Skoru:** `{skor_val}/10`"
                )
                telegram_mesaj_gonder(mesaj_metni)
            elif anlik_algoritma_yonu == "NÖTR (İZLE)":
                st.session_state[state_sinyal_key] = "NÖTR (İZLE)"
                st.session_state[state_fiyat_key] = 0.0

            # Detaylı grafik ve arayüz çizim bölümü (Yalnızca seçilen enstrüman için ekrana basılır)
            if asset_adi == secilen_forex_adi:
                strateji_yonu = st.session_state[state_sinyal_key]
                if Birds_eye := strateji_yonu == "LONG (YUKARI)":
                    ana_skor = long_skor; durum_color = "#2ECC71"; sinyal_tetik_fiyati = st.session_state[state_fiyat_key]
                    durum_msg = f"🚀 GÜÇLÜ BOĞA - {sinyal_tetik_fiyati:.4f} SEVİYESİNDEN SİNYAL SABİTLENDİ"
                    sl_noktasi = sinyal_tetik_fiyati - (atr_val * 1.5); tp_noktasi = sinyal_tetik_fiyati + (atr_val * 3.0)
                elif strateji_yonu == "SHORT (AŞAĞI)":
                    ana_skor = short_skor; durum_color = "#E74C3C"; sinyal_tetik_fiyati = st.session_state[state_fiyat_key]
                    durum_msg = f"💥 GÜÇLÜ AYI - {sinyal_tetik_fiyati:.4f} SEVİYESİNDEN SİNYAL SABİTLENDİ"
                    sl_noktasi = sinyal_tetik_fiyati + (atr_val * 1.5); tp_noktasi = sinyal_tetik_fiyati - (atr_val * 3.0)
                else:
                    ana_skor = max(long_skor, short_skor); durum_color = "#7F8C8D"; durum_msg = "⏳ SİNYAL ARANIYOR (PİYASA KUTU İÇİNDE SIKIŞTI)"
                    sl_noktasi = son_fiyat; tp_noktasi = son_fiyat

                st.markdown(f"""
                <div style="background-color: #1A1A1A; padding: 20px; border-radius: 8px; border-left: 8px solid {durum_color}; margin-bottom: 20px;">
                    <h3 style="color: white !important; margin: 0; border: none !important;">{asset_adi} Komuta Paneli</h3>
                    <p style="color: {durum_color} !important; font-size: 1.3rem !important; margin: 5px 0 0 0;">{durum_msg}</p>
                </div>
                """, unsafe_allow_html=True)

                sol_p, sag_p = st.columns([0.65, 0.35])
                with sol_p:
                    fig_fx = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.75, 0.25])
                    fig_fx.add_trace(go.Candlestick(x=df_fx.index, open=df_fx['Open'], high=df_fx['High'], low=df_fx['Low'], close=df_fx['Close'], name="Mumluk"), row=1, col=1)
                    fig_fx.add_trace(go.Scatter(x=df_fx.index, y=df_fx['box_ust'], line=dict(color='#9B59B6', width=1.5, dash='dash'), name="Box Üst Tavan"), row=1, col=1)
                    fig_fx.add_trace(go.Scatter(x=df_fx.index, y=df_fx['box_alt'], line=dict(color='#9B59B6', width=1.5, dash='dash'), name="Box Alt Taban"), row=1, col=1)
                    fig_fx.add_trace(go.Scatter(x=df_fx.index, y=df_fx['EMA21'], line=dict(color='#E67E22', width=1.2), name="EMA 21"), row=1, col=1)
                    fig_fx.add_trace(go.Scatter(x=df_fx.index, y=df_fx['EMA50'], line=dict(color='#3498DB', width=1.2), name="EMA 50"), row=1, col=1)
                    
                    if strateji_yonu != "NÖTR (İZLE)":
                        fig_fx.add_trace(go.Scatter(x=[df_fx.index[-20], df_fx.index[-1]], y=[tp_noktasi, tp_noktasi], line=dict(color='#2ECC71', width=2.5), name="Hedef (TP)"), row=1, col=1)
                        fig_fx.add_trace(go.Scatter(x=[df_fx.index[-20], df_fx.index[-1]], y=[sl_noktasi, sl_noktasi], line=dict(color='#E74C3C', width=2.5), name="Risk Sınırı (SL)"), row=1, col=1)
                    
                    fig_fx.add_trace(go.Scatter(x=df_fx.index, y=df_fx['RSI'], line=dict(color='#E74C3C', width=1.5), name="RSI Line"), row=2, col=1)
                    fig_fx.add_hline(y=70, line_dash="dot", line_color="red", row=2, col=1)
                    fig_fx.add_hline(y=30, line_dash="dot", line_color="green", row=2, col=1)
                    fig_fx.update_layout(height=650, template="plotly_white", xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
                    st.plotly_chart(fig_fx, use_container_width=True)

                with sag_p:
                    st.markdown("#### ⚡ Güç Göstergeleri")
                    st.markdown(f"**Alıcıların Baskısı (Long Skor):** `{long_skor} / 10`")
                    st.markdown(f"""
                    <div style="background-color: #E0E0E0; width: 100%; height: 8px; border-radius: 4px; margin-bottom: 20px;">
                        <div style="width: {int(long_skor*10)}%; background-color: #2ECC71; height: 100%; border-radius: 4px;"></div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"**Satıcıların Baskısı (Short Skor):** `{short_skor} / 10`")
                    st.markdown(f"""
                    <div style="background-color: #E0E0E0; width: 100%; height: 8px; border-radius: 4px; margin-bottom: 20px;">
                        <div style="width: {int(short_skor*10)}%; background-color: #E74C3C; height: 100%; border-radius: 4px;"></div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("#### 🔍 Sinyal Gerekçeleri")
                    for neden in nedenler:
                        st.write(f"- {neden}")
                    st.markdown("#### 🔬 Teknik Değerler")
                    st.write(f"**RSI Göstergesi:** {rsi_val:.2f}")
                    st.write(f"**Kristal Tavan (Box Üst):** {b_ust:.4f}")
                    st.write(f"**Kristal Taban (Box Alt):** {b_alt:.4f}")
