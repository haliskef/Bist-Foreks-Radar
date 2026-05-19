import streamlit as st
from streamlit_autorefresh import st_autorefresh
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import time
import os

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

# FOREX VE KÜRESEL PİYASALAR SÖZLÜĞÜ
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

# =================================================================================
# =================================================================================
# ÇEKİRDEK 1: LAZER MODU (MÜSTAKİL ARKA PLAN THREADİNG & ÖZGÜR MANUEL İNCELEME)
# =================================================================================
if calisma_modu == "Lazer (Detaylı Analiz & Strateji)":
    # Ekranın canlı kalması için makul bir otomatik yenileme (Sadece arayüzü günceller, taramayı kilitlemez)
    st_autorefresh(interval=30000, limit=1000, key="lazer_arayuz_tazeleyici")
    
    import time
    import threading
    import numpy as np
    import pandas as pd
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    # -----------------------------------------------------------------------------
    # 🌍 GLOBAL RADAR HAFIZASI (Arka Plan ve Ön Planın Ortak Konuştuğu Alan)
    # -----------------------------------------------------------------------------
    if "radar_canli_tablo" not in st.session_state:
        st.session_state.radar_canli_tablo = {} # Hisse -> {"puan": X, "zaman": Y, "not": Z}
    if "tarama_aktif_thread" not in st.session_state:
        st.session_state.tarama_aktif_thread = False

    bist_100_radar_listesi = [
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

    TELEGRAM_BOT_TOKEN = "8817119197:AAHcHADLXZ7DbLgJp7yskg94QO0Q6jJd85s"
    TELEGRAM_CHAT_ID = "1338802399"

    def arka_plan_telegram_gonder(mesaj):
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            try:
                import requests
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mesaj, "parse_mode": "Markdown"}
                requests.post(url, json=payload, timeout=5)
            except: pass

    # Sektörel veri hesaplayıcı (İç fonksiyonlardan izole, saf Python fonksiyonu)
    def saf_sektor_analizi(hisse_kodu):
        sektorler = {
            "HAVACILIK": ["THYAO.IS", "PGSUS.IS", "TAVHL.IS", "CLEBI.IS", "DOCO.IS"],
            "BANKACILIK": ["AKBNK.IS", "GARAN.IS", "ISCTR.IS", "YKBNK.IS", "HALKB.IS", "VAKBN.IS"],
            "OTOMOTİV": ["FROTO.IS", "TOASO.IS", "DOAS.IS", "KARSN.IS", "TTRAK.IS", "OTKAR.IS"],
            "ENERJİ": ["ENJSA.IS", "ASTOR.IS", "AKSEN.IS", "GWIND.IS", "SMRTG.IS", "ALFAS.IS", "CWENE.IS", "EUPWR.IS", "ODAS.IS", "GESAN.IS"],
            "HOLDİNG": ["KCHOL.IS", "SAHOL.IS", "ALARK.IS", "DOHOL.IS", "AGHOL.IS", "TKFEN.IS", "ENKAI.IS"],
            "DEMİR-ÇELİK": ["EREGL.IS", "KRDMD.IS", "ISDMR.IS", "KCAER.IS", "BRSAN.IS"],
            "PERAKENDE": ["BIMAS.IS", "MGROS.IS", "SOKM.IS", "MAVI.IS"],
            "KİMYA & PETROL": ["AKSA.IS", "GUBRF.IS", "HEKTS.IS", "KMPUR.IS", "PETKM.IS", "SASA.IS", "TUPRS.IS"]
        }
        bulunan = "DİĞER"
        for sek, h_list in sektorler.items():
            if hisse_kodu in h_list: bulunan = sek; break
        return bulunan

    # -----------------------------------------------------------------------------
    # OTONOM MOTOR: ANA SİSTEMDEN BAĞIMSIZ ARKA PLAN THREAD DÖNGÜSÜ
    # -----------------------------------------------------------------------------
    def otonom_radar_tarama_motoru(canli_tablo_ref):
        """ Tamamen izole iş parçacığı. Streamlit arayüzünü asla yavaşlatmaz veya dondurmaz. """
        while True:
            for r_hisse in bist_100_radar_listesi:
                try:
                    # Sessizce yfinance üzerinden tek tek çekim yap (Saniyede 1 istek limiti aşılmasın diye kontrollü)
                    ticker = yf.Ticker(r_hisse)
                    df_r = ticker.history(period="1mo", interval="1d")
                    if df_r.empty or len(df_r) < 5: continue
                    if isinstance(df_r.columns, pd.MultiIndex): df_r.columns = df_r.columns.get_level_values(0)
                    df_r.columns = [str(c).strip().capitalize() for c in df_r.columns]

                    # Göstergeler
                    df_r['EMA50'] = df_r['Close'].ewm(span=50, adjust=False).mean()
                    delta_r = df_r['Close'].diff()
                    gain_r = delta_r.clip(lower=0)
                    loss_r = -delta_r.clip(upper=0)
                    df_r['RSI'] = 100 - (100 / (1 + (gain_r.ewm(com=13, adjust=False).mean() / loss_r.ewm(com=13, adjust=False).mean())))
                    
                    r_fiyat = float(df_r['Close'].iloc[-1])
                    r_rsi = float(df_r['RSI'].iloc[-1])
                    
                    # Puanlama Rasyoları
                    info_r = ticker.info
                    r_fk = info_r.get('trailingPE', None)
                    r_pddd = info_r.get('priceToBook', None)
                    r_roe = info_r.get('returnOnEquity', None)

                    r_puan = 0.0
                    r_maddeler = []

                    if r_fk and 0 < r_fk < 15: r_puan += 1.5; r_maddeler.append(f"📊 F/K Çarpanı Dengeli ({r_fk:.1f})")
                    if r_pddd and 0 < r_pddd < 3.5: r_puan += 1.0; r_maddeler.append(f"📑 PD/DD Güvenli Alanda ({r_pddd:.1f})")
                    if r_roe and r_roe > 0.30: r_puan += 1.5; r_maddeler.append(f"💰 ROE / Özsermaye Kârlılığı Güçlü (%{r_roe*100:.1f})")
                    if 30 <= r_rsi <= 45: r_puan += 2.0; r_maddeler.append(f"🎯 RSI Toplama Kıvamında ({r_rsi:.1f})")
                    elif r_rsi < 30: r_puan += 1.5; r_maddeler.append(f"🔥 Aşırı Satış Bölgesinde")
                    if r_fiyat > df_r['EMA50'].iloc[-1]: r_puan += 1.0; r_maddeler.append("📈 Fiyat EMA50 Üzerinde")

                    r_puan = min(10.0, max(0.0, round(r_puan, 1)))
                    hisse_temiz = r_hisse.replace('.IS', '')

                    # Eski durum kontrolü (Histerezis kilit kontrolü için)
                    eski_durum = canli_tablo_ref.get(hisse_temiz, {}).get("durum", "NÖTR")

                    # Hafızayı Güncelle (Arayüz görsün diye)
                    canli_tablo_ref[hisse_temiz] = {
                        "fiyat": r_fiyat,
                        "puan": r_puan,
                        "rsi": r_rsi,
                        "durum": "SAMPİYON" if r_puan >= 7.5 else ("GUCLU" if r_puan >= 6.5 else "IZLE")
                    }

                    # TELEGRAM FİLTER MOTORU (Sadece ilk defa barajı geçenler veya Nötrden buraya gelenler)
                    if r_puan >= 6.5 and eski_durum == "IZLE":
                        durum_etiketi = "👑 #SAMPİYON (MÜKEMMEL KURULUM)" if r_puan >= 7.5 else "🟢 #GUCLU (YÜKSEK POTANSİYEL)"
                        gerekceler_metni = "\n".join(r_maddeler)
                        radar_mesaj = (
                            f"🎯 *BIST 100 DERİN RADAR TARAMASI*\n\n"
                            f"**Sinyal Sınıfı:** {durum_etiketi}\n"
                            f"**Hisse:** #{hisse_temiz}\n"
                            f"**Anlık Fiyat:** `{r_fiyat:.2f} TL`\n"
                            f"**Yapay Zeka Puanı:** `{r_puan} / 10`\n\n"
                            f"**🔍 Analiz Gerekçeleri:**\n{gerekceler_metni}"
                        )
                        arka_plan_telegram_gonder(radar_mesaj)

                    time.sleep(4) # Ban yememek ve işlemciyi yormamak için her hisse arası güvenli boşluk
                except:
                    time.sleep(2)
            time.sleep(30) # Tüm liste bittiğinde yeni tarama döngüsüne geçmeden önce soğuma payı

    # Thread başlatıcı kontrol mekanizması (Streamlit yenilendikçe kopyalanmayı engeller)
    if not st.session_state.tarama_aktif_thread:
        t = threading.Thread(target=otonom_radar_tarama_motoru, args=(st.session_state.radar_canli_tablo,), daemon=True)
        t.start()
        st.session_state.tarama_aktif_thread = True

    # -----------------------------------------------------------------------------
    # 🖥️ GÖRSEL PANEL: ÜST KISIM - RADAR CANLI AKIŞ TAKİPÇİSİ (Arka Planın Çıktıları)
    # -----------------------------------------------------------------------------
    with st.expander("🛰️ ARKA PLAN CANLI TARAMA DURUMU (Yapay Zeka Radarına Yakalananlar)", expanded=False):
        if st.session_state.radar_canli_tablo:
            radar_df_data = []
            for k, v in st.session_state.radar_canli_tablo.items():
                radar_df_data.append({"Hisse": k, "Fiyat": v["fiyat"], "RSI": round(v["rsi"],1), "YZ Puanı": v["puan"], "Sistem Sinyali": v["durum"]})
            rdf = pd.DataFrame(radar_df_data).sort_values(by="YZ Puanı", ascending=False).reset_index(drop=True)
            st.dataframe(rdf.style.map(lambda x: 'background-color: #FFD700; color: black; font-weight: bold;' if x=="SAMPİYON" else ('background-color: #C8E6C9; color: black;' if x=="GUCLU" else ''), subset=['Sistem Sinyali']), use_container_width=True)
        else:
            st.info("Arka plan tarama motoru ilk döngüyü gerçekleştiriyor... Veriler birazdan burada belirecek.")

    # -----------------------------------------------------------------------------
    # ⚙️ MANUEL SEÇİM ALANI (Sen İstediğini Yaz, Arka Plan Seni Engellemez)
    # -----------------------------------------------------------------------------
    with st.sidebar:
        st.markdown("### ⚙️ MANUEL HİSSE İNCELEME")
        hisse = st.text_input("HİSSE KODU (Kendin Değiştir)", "THYAO.IS").upper()
        zaman_sozlugu = {"15 Dikika": "15m", "1 Saat": "1h", "1 Gün": "1d"}
        secilen_int = st.selectbox("VERİ SIKLIĞI", list(zaman_sozlugu.keys()), index=2)
        view_period = st.selectbox("GÖRÜNÜM ARALIĞI", ["1 Ay", "3 Ay", "6 Ay", "1 Yıl", "Tümü"], index=2)

    # -----------------------------------------------------------------------------
    # SEÇİLEN TEK HİSSENİN GRAFİKSEL VE MATRİSSEL DERİN ANALİZİ
    # -----------------------------------------------------------------------------
    @st.cache_data(ttl=30) # Manuel incelediğin hissenin verisi grafik donmasın diye 30sn önbelleğe alınır
    def get_manuel_hisse_data(kod, interval):
        try:
            ticker = yf.Ticker(kod)
            p = "2y" if interval in ["1h", "1d"] else "1mo"
            data = ticker.history(period=p, interval=interval)
            if data.empty: return pd.DataFrame(), {}
            if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
            data.columns = [str(c).strip().capitalize() for c in data.columns]
            return data, ticker.info
        except: return pd.DataFrame(), {}

    df_all, info_data = get_manuel_hisse_data(hisse, zaman_sozlugu[secilen_int])

    if df_all.empty or 'Close' not in df_all.columns:
        st.error(f"⚠️ {hisse} kodu için canlı piyasa verisi okunamadı. Lütfen kodu kontrol edin veya sayfayı tazeleyin.")
    else:
        df = df_all.copy()
        
        # Göstergelerin Hesaplanması
        df['EMA7'] = df['Close'].ewm(span=7, adjust=False).mean()
        df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
        df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['EMA100'] = df['Close'].ewm(span=100, adjust=False).mean()
        
        delta = df['Close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        df['RSI'] = 100 - (100 / (1 + (gain.ewm(com=13, adjust=False).mean() / loss.ewm(com=13, adjust=False).mean())))
        
        ema12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD_H'] = (ema12 - ema26) - (ema12 - ema26).ewm(span=9, adjust=False).mean()

        # Grafik Görünüm Filtresi
        if view_period == "1 Ay": df_plot = df.tail(30).copy()
        elif view_period == "3 Ay": df_plot = df.tail(90).copy()
        elif view_period == "6 Ay": df_plot = df.tail(180).copy()
        else: df_plot = df.copy()

        son_fiyat = df['Close'].iloc[-1].item()
        rsi_val = df['RSI'].iloc[-1].item()

        # Trend Kanal Çizimleri
        x = np.arange(len(df_plot))
        y = df_plot['Close'].values
        slope, intercept = np.polyfit(x, y, 1) if len(x) > 1 else (0, son_fiyat)
        df_plot['Orta_Trend'] = slope * x + intercept
        sapma = np.std(y - df_plot['Orta_Trend']) if len(x) > 1 else 0
        df_plot['Ust_Trend'] = df_plot['Orta_Trend'] + (sapma * 2)
        df_plot['Alt_Trend'] = df_plot['Orta_Trend'] - (sapma * 2)

        # PLOTLY ŞAHANE CANDLESTICK GRAFİĞİ
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.06, row_heights=[0.75, 0.25])
        fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name="Fiyat"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['Ust_Trend'], name="Kanal Üst", line=dict(color='orange', width=1, dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['Alt_Trend'], name="Kanal Alt", line=dict(color='orange', width=1, dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA21'], name="EMA 21", line=dict(color='blue', width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['EMA50'], name="EMA 50", line=dict(color='red', width=1.5, dash='dash')), row=1, col=1)
        
        # MACD Alt Grafiğe
        colors = ['green' if val >= 0 else 'red' for val in df_plot['MACD_H']]
        fig.add_trace(go.Bar(x=df_plot.index, y=df_plot['MACD_H'], name="MACD Histogram", marker_color=colors), row=2, col=1)
        
        fig.update_layout(height=600, template="plotly_white", xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

        # -----------------------------------------------------------------------------
        # METRİK KARTLARI VE MALİ RÖNTGEN
        # -----------------------------------------------------------------------------
        st.markdown("### 📊 ANLIK TEKNİK MATRİS")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("FİYAT", f"{son_fiyat:.2f} TL")
        m2.metric("EMA 50", f"{df['EMA50'].iloc[-1]:.2f}")
        m3.metric("RSI (14)", f"{rsi_val:.1f}")
        m4.metric("KANAL ÜST", f"{df_plot['Ust_Trend'].iloc[-1]:.2f}")
        m5.metric("KANAL ALT", f"{df_plot['Alt_Trend'].iloc[-1]:.2f}")

        fk_val = info_data.get('trailingPE', 'N/A')
        pddd_val = info_data.get('priceToBook', 'N/A')
        roe_val = info_data.get('returnOnEquity', None)

        st.markdown("### 🏢 SİZİN SEÇTİĞİNİZ HİSSENİN TEMEL DEĞERLERİ")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("F/K", f"{fk_val:.2f}" if isinstance(fk_val, float) else "N/A")
        k2.metric("PD/DD", f"{pddd_val:.2f}" if isinstance(pddd_val, float) else "N/A")
        k3.metric("Sektör", saf_sektor_analizi(hisse))
        k4.metric("ROE (Özsermaye Kâr.)", f"%{roe_val*100:.1f}" if roe_val else "N/A")

        # Karar Motoru Hesaplaması (Ekran İçin)
        ekran_puan = 0.0
        if isinstance(fk_val, float) and fk_val < 15: ekran_puan += 2.0
        if isinstance(pddd_val, float) and pddd_val < 3.5: ekran_puan += 1.5
        if roe_val and roe_val > 0.30: ekran_puan += 1.5
        if 30 <= rsi_val <= 45: ekran_puan += 2.0
        if son_fiyat > df['EMA50'].iloc[-1]: ekran_puan += 1.5
        if slope > 0: ekran_puan += 1.5
        ekran_puan = min(10.0, round(ekran_puan, 1))

        st.markdown(f"""
        <div class='ai-score-box' style='background-color: #1E1E2F; padding: 20px; border-radius: 10px; border: 1px solid #3E3E5F;'>
            <h3 style='color: white; margin-top:0;'>🤖 MANUEL İNCELEME YAPAY ZEKA SKORU</h3>
            <h2 style='color: #FFD700; margin: 0;'>{ekran_puan} / 10</h2>
            <p style='color: #CCCCCC; font-size: 0.95rem; margin-top: 10px;'>
                Bu puanlama tamamen senin ekranda seçtiğin <b>{hisse}</b> hissesine aittir. Arka plandaki otonom radar sistemi buradaki seçimlerinden bağımsız olarak BIST 100 taramasına ve Telegram sinyallerine devam eder.
            </p>
        </div>
        """, unsafe_allow_html=True)


# =================================================================================
# =================================================================================
# ÇEKİRDEK 3: FOREX & KÜRESEL PİYASALAR (TAM OTONOM ÇOKLU ENSTRÜMAN RADARI - ESKİ KORUMALI)
# =================================================================================
elif calisma_modu == "Forex & Küresel Piyasalar (Çift Yönlü)":
    st_autorefresh(interval=60000, key="global_forex_multi_scan_v11_protected")
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
        # Sabit Test Butonun (En üstte güvenle duruyor)
        if st.button("🚀 Sistem Bildirim Testini Tetikle"):
            try:
                import requests
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
                payload = {"chat_id": TELEGRAM_CHAT_ID, "text": "🎯 *SİSTEM TESTİ BAŞARILI!*\n\nÇoklu tarama modunda Telegram hattınız aktiftir.", "parse_mode": "Markdown"}
                response = requests.post(url, json=payload, timeout=5)
                if response.status_code == 200: st.success("🎯 Harika! Mesaj başarıyla gönderildi. Telefonunu kontrol et.")
                else: st.error(f"❌ Telegram API Hata Döndürdü: {response.text}")
            except Exception as e: st.error(f"🚨 Sunucu/Ağ Bağlantı Hatası: {e}")

        st.info("🔄 **7/24 Arka Plan Tarayıcısı Aktif:** Menüde hangi enstrüman seçili olursa olsun, sistem arka planda tüm listeyi tarar ve herhangi birinde kırılım (sinyal) oluşursa anında cebinize gönderir.")
        
        # Ekranda detaylarını, nedenlerini ve grafiğini görmek istediğin enstrüman seçimi
        secilen_forex_adi = st.selectbox("Ekranda Detaylı İncelemek İstediğiniz Küresel Enstrüman:", list(forex_assets.keys()))
        
        # 🤖 OTONOM ÇOKLU TARAMA DÖNGÜSÜ (Listeyi sırayla döner ama tüm mantığı korur)
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
                if isinstance(df_fx.columns, pd.MultiIndex): df_fx.columns = df_fx.columns.get_level_values(0)
                df_fx.columns = [str(c).strip().capitalize() for c in df_fx.columns]
                
                # 1. Kristal Box Hesaplamaları (Donchian) - TAMAMI KORUNDU
                df_fx['box_ust'] = df_fx['High'].rolling(window=20).max()
                df_fx['box_alt'] = df_fx['Low'].rolling(window=20).min()
                df_fx['box_orta'] = (df_fx['box_ust'] + df_fx['box_alt']) / 2
                
                # 2. Native ATR & Teknik İndikatör Hesaplamaları - TAMAMI KORUNDU
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
                
                # 3. PRICE ACTION SINIFLANDIRICI KATMANI - TAMAMI KORUNDU
                son_mum = df_fx.iloc[-1]
                onceki_mum = df_fx.iloc[-2]
                
                mum_boyu = son_mum['High'] - son_mum['Low']
                alt_fitil = min(son_mum['Open'], son_mum['Close']) - son_mum['Low']
                ust_fitil = son_mum['High'] - max(son_mum['Open'], son_mum['Close'])
                
                is_bullish_pin = (alt_fitil / mum_boyu) > 0.60 if mum_boyu > 0 else False
                is_bearish_pin = (ust_fitil / mum_boyu) > 0.60 if mum_boyu > 0 else False
                is_bullish_engulfing = (onceki_mum['Close'] < onceki_mum['Open']) and (son_mum['Close'] > son_mum['Open']) and (son_mum['Close'] > onceki_mum['Open'])
                is_bearish_engulfing = (onceki_mum['Close'] > onceki_mum['Open']) and (son_mum['Close'] < son_mum['Open']) and (son_mum['Close'] < onceki_mum['Open'])
                
                son_ekstrem_zirve = df_fx['High'].tail(15).iloc[:-1].max()
                son_ekstrem_dip = df_fx['Low'].tail(15).iloc[:-1].min()
                is_msb_bullish = son_fiyat > son_ekstrem_zirve
                is_msb_bearish = son_fiyat < son_ekstrem_dip

                # 4. ÇİFT YÖNLÜ KARAR MOTORU - TAMAMI KORUNDU
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

                if is_bullish_pin: long_skor += 1.5; nedenler.append("🔥 PRICE ACTION: Boğa Pin Bar oluştu")
                if is_bullish_engulfing: long_skor += 1.5; nedenler.append("🔥 PRICE ACTION: Bullish Engulfing görüldü")
                if is_msb_bullish: long_skor += 1.0; nedenler.append("⚔️ PRICE ACTION: Market Yapısı Boğa yönlü kırıldı (MSB/CHoCH)")
                    
                if is_bearish_pin: short_skor += 1.5; nedenler.append("❄️ PRICE ACTION: Ayı Pin Bar oluştu")
                if is_bearish_engulfing: short_skor += 1.5; nedenler.append("❄️ PRICE ACTION: Bearish Engulfing görüldü")
                if is_msb_bearish: short_skor += 1.0; nedenler.append("⚔️ PRICE ACTION: Market Yapısı Ayı yönlü kırıldı (MSB/CHoCH)")

                long_skor = min(10.0, round(long_skor, 1))
                short_skor = min(10.0, round(short_skor, 1))

                anlik_algoritma_yonu = "NÖTR (İZLE)"
                if long_skor >= 7.0 and long_skor >= short_skor:
                    anlik_algoritma_yonu = "LONG (YUKARI)"
                elif short_skor >= 7.0 and short_skor > long_skor:
                    anlik_algoritma_yonu = "SHORT (AŞAĞI)"

                # AKILLI BELLEK KİLİTLEME & ARKA PLAN TELEGRAM BİLDİRİM TETİKLEYİCİ
                if anlik_algoritma_yonu != "NÖTR (İZLE)" and st.session_state[state_sinyal_key] == "NÖTR (İZLE)":
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
                        sl_noktasi = sinyal_tetik_fiyati - (atr_val * 1.5); tp_noktasi = sinyal_tetik_fiyati + (atr_val * 3.0)
                    elif strateji_yonu == "SHORT (AŞAĞI)":
                        ana_skor = short_skor; durum_color = "#E74C3C"; sinyal_tetik_fiyati = st.session_state[state_fiyat_key]
                        durum_msg = f"💥 GÜÇLÜ AYI - {sinyal_tetik_fiyati:.4f} SEVİYESİNDEN AÇIĞA SATIŞ SABİTLENDİ"
                        sl_noktasi = sinyal_tetik_fiyati + (atr_val * 1.5); tp_noktasi = sinyal_tetik_fiyati - (atr_val * 3.0)
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
                        st.markdown(f"""
                        <div style="width: 100%; background-color: #E0E0E0; height: 8px; border-radius: 4px; margin-bottom: 12px;">
                            <div style="width: {int(long_skor*10)}%; background-color: #2ECC71; height: 100%; border-radius: 4px;"></div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.markdown(f"**🔴 Short Algoritma Ağırlığı:** `{short_skor} / 10`")
                        st.markdown(f"""
                        <div style="width: 100%; background-color: #E0E0E0; height: 8px; border-radius: 4px; margin-bottom: 20px;">
                            <div style="width: {int(short_skor*10)}%; background-color: #E74C3C; height: 100%; border-radius: 4px;"></div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.markdown("#### 🔍 Sinyal Gerekçeleri")
                        for neden in nedenler: st.write(f"- {neden}")
                            
                        st.markdown("#### 🔬 Teknik Değerler")
                        st.write(f"**RSI Göstergesi:** {rsi_val:.2f}")
                        st.write(f"**Kristal Tavan (Box Üst):** {b_ust:.4f}")
                        st.write(f"**Kristal Taban (Box Alt):** {b_alt:.4f}")

                    with sag_p:
                        st.markdown("### 📈 Çift Yönlü Grafik ve Hedef Haritası")
                        fig_fx = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.06, row_heights=[0.7, 0.3])
                        fig_fx.add_trace(go.Candlestick(x=df_fx.index, open=df_fx['Open'], high=df_fx['High'], low=df_fx['Low'], close=df_fx['Close'], name="Fiyat"), row=1, col=1)
                        fig_fx.add_trace(go.Scatter(x=df_fx.index, y=df_fx['box_ust'], line=dict(color='#8E44AD', width=1.5, dash='dash'), name="Box Üst Tavan"), row=1, col=1)
                        fig_fx.add_trace(go.Scatter(x=df_fx.index, y=df_fx['box_alt'], line=dict(color='#8E44AD', width=1.5, dash='dash'), name="Box Alt Taban"), row=1, col=1)
                        fig_fx.add_trace(go.Scatter(x=df_fx.index, y=df_fx['EMA21'], line=dict(color='#E67E22', width=1.2), name="EMA 21"), row=1, col=1)
                        fig_fx.add_trace(go.Scatter(x=df_fx.index, y=df_fx['EMA50'], line=dict(color='#3498DB', width=1.2), name="EMA 50"), row=1, col=1)
                        
                        if strateji_yonu != "NÖTR (İZLE)":
                            fig_fx.add_trace(go.Scatter(x=[df_fx.index[-20], df_fx.index[-1]], y=[tp_noktasi, tp_noktasi], line=dict(color='#2ECC71', width=2.5), name="Hedef (TP)"), row=1, col=1)
                            fig_fx.add_trace(go.Scatter(x=[df_fx.index[-20], df_fx.index[-1]], y=[sl_noktasi, sl_noktasi], line=dict(color='#E74C3C', width=2.5), name="Risk Sınırı (SL)"), row=1, col=1)
                            fig_fx.add_trace(go.Scatter(x=[df_fx.index[-20], df_fx.index[-1]], y=[sinyal_tetik_fiyati, sinyal_tetik_fiyati], line=dict(color='#111111', width=2, dash='dot'), name="Sabit Giriş Seviyesi"), row=1, col=1)
                        
                        fig_fx.add_trace(go.Scatter(x=df_fx.index, y=df_fx['RSI'], line=dict(color='#16A085', width=1.5), name="RSI"), row=2, col=1)
                        fig_fx.update_layout(xaxis_rangeslider_visible=False, height=650, template="plotly_white", margin=dict(l=10, r=10, t=10, b=10))
                        st.plotly_chart(fig_fx, use_container_width=True)
