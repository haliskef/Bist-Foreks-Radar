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
    
    .ai-comment-box {
        background-color: #FFFFFF !important; padding: 18px; border-radius: 12px;
        border-left: 5px solid #1A1A1A; border-top: 1px solid #E0E0E0;
        border-right: 1px solid #E0E0E0; border-bottom: 1px solid #E0E0E0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.05); margin-top: 15px; margin-bottom: 15px;
    }
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
    "BRENT PETROL": "BZ=F",
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "BTC/USD": "BTC-USD",
    "S&P 500": "^GSPC",
    "NASDAQ 100": "^NDX",
    "DXY (Dolar Endeksi)": "DX-Y.NYB",
    "DAX 40 (Almanya)": "^GDAXI"
}

# =================================================================================
# ÇEKİRDEK 1: LAZER MODU (DETAYLI ANALİZ & STRATEJİ)
# =================================================================================
if calisma_modu == "Lazer (Detaylı Analiz & Strateji)":
    st_autorefresh(interval=30000, limit=500, key="bist_guncelleme")
    
    with st.sidebar:
        st.markdown("### ⚙️ HİSSE PARAMETRELERİ")
        hisse = st.text_input("HİSSE KODU", "THYAO.IS").upper()
        zaman_sozlugu = {"15 Dakika": "15m", "1 Saat": "1h", "1 Gün": "1d"}
        secilen_int = st.selectbox("VERİ SIKLIĞI", list(zaman_sozlugu.keys()), index=2)
        view_period = st.selectbox("GÖRÜNÜM ARALIĞI", ["1 Ay", "3 Ay", "6 Ay", "1 Yıl", "Tümü"], index=2)

    @st.cache_data(ttl=15)
    def get_full_data(kod, interval):
        try:
            ticker = yf.Ticker(kod)
            p = "2y" if interval in ["1h", "1d"] else "1mo"
            data = ticker.history(period=p, interval=interval)
            info = ticker.info
            if data.empty: return pd.DataFrame(), {}
            if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
            data.columns = [str(c).strip().capitalize() for c in data.columns]
            try:
                if data.index.tzinfo is None: data.index = data.index.tz_localize('UTC').tz_convert('Europe/Istanbul')
                else: data.index = data.index.tz_convert('Europe/Istanbul')
            except: pass
            return data, info
        except: return pd.DataFrame(), {}

    @st.cache_data(ttl=3600)
    def otonom_sektor_hesapla(hisse_kodu):
        sektorler = {
            "HAVACILIK": ["THYAO.IS", "PGSUS.IS", "TAVHL.IS", "CLEBI.IS", "DOCO.IS"],
            "BANKACILIK": ["AKBNK.IS", "GARAN.IS", "ISCTR.IS", "YKBNK.IS", "HALKB.IS", "VAKBN.IS", "ALBRK.IS", "SKBNK.IS", "TSKB.IS"],
            "OTOMOTİV & YAN SANAYİ": ["FROTO.IS", "TOASO.IS", "DOAS.IS", "KARSN.IS", "ASUZU.IS", "TTRAK.IS", "OTKAR.IS", "BRISA.IS", "EGEEN.IS"],
            "ENERJİ & GAZ": ["ENJSA.IS", "ASTOR.IS", "AKSEN.IS", "GWIND.IS", "SMRTG.IS", "ALFAS.IS", "CWENE.IS", "EUPWR.IS", "HUNER.IS", "ZOREN.IS", "ODAS.IS", "CANTE.IS", "AYDEM.IS", "GESAN.IS", "KARYE.IS", "NATEN.IS", "ENERY.IS", "IZENR.IS", "AYGAZ.IS", "CONSE.IS", "MAGEN.IS", "ESEN.IS", "BIOEN.IS", "CATES.IS", "SUNTK.IS"],
            "HOLDİNG & YATIRIM": ["KCHOL.IS", "SAHOL.IS", "ALARK.IS", "DOHOL.IS", "AGHOL.IS", "TKFEN.IS", "ENKAI.IS", "NTHOL.IS", "BERA.IS", "GLYHO.IS"],
            "DEMİR-ÇELİK": ["EREGL.IS", "KRDMD.IS", "ISDMR.IS", "KCAER.IS", "BRSAN.IS", "CEMAS.IS"],
            "PERAKENDE & TİCARET": ["BIMAS.IS", "MGROS.IS", "SOKM.IS", "CRFSA.IS", "MAVI.IS"],
            "ÇİMENTO & CAM & SERAMİK": ["AKCNS.IS", "CIMSA.IS", "OYAKC.IS", "BUCIM.IS", "BTCIM.IS", "BIENY.IS", "KALES.IS", "QUAGR.IS", "SISE.IS", "KONYA.IS"],
            "TELEKOMÜNİKASYON": ["TCELL.IS", "TTKOM.IS"],
            "GIDA & İÇECEK": ["CCOLA.IS", "AEFES.IS", "ULKER.IS", "TABGD.IS", "TUKAS.IS", "TATGD.IS", "PETUN.IS", "YYLGD.IS", "FADAG.IS"],
            "TEKNOLOJİ & BİLİŞİM": ["HKTM.IS", "KONTR.IS", "MIATK.IS", "PENTA.IS", "ARDYZ.IS", "VBTYZ.IS", "MTRKS.IS"],
            "SAVUNMA SANAYİ": ["ASELS.IS", "SDTTR.IS"],
            "KİMYA & PETROKİMYA & GÜBRE": ["AKSA.IS", "BAGFS.IS", "GUBRF.IS", "HEKTS.IS", "KMPUR.IS", "PETKM.IS", "SASA.IS", "TUPRS.IS"],
            "GAYRİMENKUL YATIRIM (GYO)": ["AKFGY.IS", "EKGYO.IS", "HLGYO.IS", "ISGYO.IS", "KZBGY.IS", "TRGYO.IS", "ZRGYO.IS"],
            "MADENCİLİK": ["IPEKE.IS", "KOZAA.IS", "KOZAL.IS", "PRKME.IS"],
            "DAYANIKLI TÜKETİM & ELEKTRONİK": ["ARCLK.IS", "VESBE.IS", "VESTL.IS"],
            "İLAÇ & SAĞLIK": ["ECILC.IS", "GENIL.IS", "DEVA.IS", "MPARK.IS", "LKMNH.IS"],
            "ARACI KURUMLAR & FİNANS": ["ISMEN.IS", "INFO.IS", "OYAYO.IS"],
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

    df_all, info_data = get_full_data(hisse, zaman_sozlugu[secilen_int])

    if not df_all.empty and 'Close' in df_all.columns:
        df = df_all.copy()
        
        # OTONOM TEKNİK HESAPLAMALAR (SAF PANDAS)
        df['EMA7'] = df['Close'].ewm(span=7, adjust=False).mean()
        df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
        df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['EMA100'] = df['Close'].ewm(span=100, adjust=False).mean()
        df['EMA200'] = df['Close'].ewm(span=200, adjust=False).mean()
        
        # SAF PANDAS RSI HESAPLAMA
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / (loss + 1e-9)
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # SAF PANDAS MACD HESAPLAMA
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD_12_26_9'] = exp1 - exp2
        df['MACDs_12_26_9'] = df['MACD_12_26_9'].ewm(span=9, adjust=False).mean()
        df['MACDh_12_26_9'] = df['MACD_12_26_9'] - df['MACDs_12_26_9']
        
        if view_period == "1 Ay": df_plot = df.tail(30 if secilen_int == "1 Gün" else 150).copy()
        elif view_period == "3 Ay": df_plot = df.tail(90 if secilen_int == "1 Gün" else 400).copy()
        elif view_period == "6 Ay": df_plot = df.tail(180).copy()
        elif view_period == "1 Yıl": df_plot = df.tail(365).copy()
        else: df_plot = df.copy()

        son_fiyat = df['Close'].iloc[-1].item()
        rsi_val = df['RSI'].iloc[-1].item()

        try:
            bugun = df_all.index[-1].date()
            gun_verisi = df_all[df_all.index.date == bugun]
            gun_acilisi = gun_verisi['Open'].iloc[0].item()
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

        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])
        fig.add_trace(go.Candlestick(x=df_plot.index, open=df_plot['Open'], high=df_plot['High'], low=df_plot['Low'], close=df_plot['Close'], name="Fiyat", increasing_line_color='#00C853', increasing_fillcolor='#00C853', decreasing_line_color='#D50000', decreasing_fillcolor='#D50000'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['Ust_Trend'], name="Kanal Üst", line=dict(color='rgba(255, 152, 0, 0.8)', width=2, dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['Alt_Trend'], name="Kanal Alt", line=dict(color='rgba(255, 152, 0, 0.8)', width=2, dash='dot')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df_plot.index, y=df_plot['Alt_Trend'], fill='tonexty', fillcolor='rgba(255, 152, 0, 0.08)', line=dict(color='rgba(255,255,255,0)'), name="Kanal İçi", showlegend=False), row=1, col=1)
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
        
        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])], showspikes=True, spikemode="across", spikedash="dot", fixedrange=False)
        fig.update_yaxes(showspikes=True, spikemode="across", spikedash="dot", fixedrange=False)
        fig.update_layout(height=700, template="plotly_white", xaxis_rangeslider_visible=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='#FFFFFF', margin=dict(l=10, r=60, t=10, b=10), hovermode="x unified", dragmode="zoom")
        st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': True})

        if kanal_renk == "green": st.success(kanal_durumu)
        elif kanal_renk == "red": st.error(kanal_durumu)
        elif kanal_renk == "orange": st.warning(kanal_durumu)

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

        # SEKTÖREL KIYASLAMA METNİ VE GEÇİCİ DEĞİŞKEN
        sektor_durum_metni = ""
        if oto_sektor_fk:
            if isinstance(fk_val, float):
                if fk_val < oto_sektor_fk:
                    st.success(f"✅ **UCUZ:** Hissenin F/K'sı ({fk_val:.2f}), {sektor_adi} sektör ortalamasının ({oto_sektor_fk}) altında.")
                    sektor_durum_metni = "Hisse, sektörel bazda çarpan olarak ucuz fiyatlanıyor."
                else:
                    st.warning(f"⚠️ **PAHALI:** Hissenin F/K'sı ({fk_val:.2f}), {sektor_adi} sektör ortalamasının ({oto_sektor_fk}) üzerinde.")
                    sektor_durum_metni = "Hisse, sektörel rakiplerine göre primli/pahalı işlem görüyor."
        
        # ---------------------------------------------------------------------------------
        # YAPAY ZEKA HİBRİT KARAR MOTORU SKORLAMA VE YAZILIMSAL GEREKÇELENDİRME PANELİ
        # ---------------------------------------------------------------------------------
        ai_puan = 0.0
        gerekceler = []
        
        if isinstance(fk_val, float) and fk_val > 0:
            if oto_sektor_fk and fk_val < oto_sektor_fk: 
                ai_puan += 1.5
                gerekceler.append("🟩 Temel Analiz: F/K oranı sektörel ortalamanın altında (+1.5 Puan)")
            elif fk_val < 15: 
                ai_puan += 1.0
                gerekceler.append("🟩 Temel Analiz: F/K çarpanı makul sınır olan 15'in altında (+1.0 Puan)")
        
        if isinstance(pddd_val, float) and 0 < pddd_val < 3.5: 
            ai_puan += 1.0
            gerekceler.append("🟩 Temel Analiz: PD/DD oranı defter değerine yakın ve güvenli bölgede (+1.0 Puan)")
            
        if roe_val:
            if roe_val > 0.30: 
                ai_puan += 1.5
                gerekceler.append("🟩 Mali Yapı: Özsermaye Kârlılığı (ROE) %30 üstünde, mükemmel büyüme gücü (+1.5 Puan)")
            elif roe_val > 0.15: 
                ai_puan += 1.0
                gerekceler.append("🟩 Mali Yapı: Özsermaye Kârlılığı (ROE) %15 üstünde, istikrarlı getiri (+1.0 Puan)")
                
        if favok_marji and favok_marji > 0.15: 
            ai_puan += 1.0
            gerekceler.append("🟩 Operasyonel Güç: FAVÖK Marjı %15'in üzerinde, ana faaliyet kârlılığı güçlü (+1.0 Puan)")

        if 30 <= rsi_val <= 45: 
            ai_puan += 2.0  
            gerekceler.append("🟩 Teknik İndikatör: RSI toplama/akümülasyon bölgesinde (30-45), risk düşük (+2.0 Puan)")
        elif 45 < rsi_val <= 60: 
            ai_puan += 1.0 
            gerekceler.append("🟩 Teknik İndikatör: RSI nötr/pozitif momentum bölgesinde, dengeli seyir (+1.0 Puan)")
        elif rsi_val < 30: 
            ai_puan += 1.5       
            gerekceler.append("⚠️ Teknik İndikatör: RSI aşırı satım bölgesinde (<30), tepki yükselişi gelebilir (+1.5 Puan)")
        
        if son_fiyat > df['EMA50'].iloc[-1]: 
            ai_puan += 1.0 
            gerekceler.append("🟩 Trend Analizi: Fiyat orta vadeli dinamik destek olan EMA 50 üzerinde (+1.0 Puan)")
            
        if slope > 0: 
            ai_puan += 1.0 
            gerekceler.append("🟩 Regresyon: Doğrusal trend yönü pozitif/yukarı yönlü (+1.0 Puan)")
        
        fibo_618 = fib_seviyeleri['61.8%']
        ema_100 = df['EMA100'].iloc[-1]
        fibo_fark = abs((son_fiyat - fibo_618) / fibo_618) if fibo_618 != 0 else 1
        ema100_fark = abs((son_fiyat - ema_100) / ema_100) if ema_100 != 0 else 1
        
        if fibo_fark <= 0.05 or ema100_fark <= 0.05: 
            ai_puan += 1.0 
            gerekceler.append("🎯 Stratejik Konum: Fiyat kritik Fibonacci %61.8 veya EMA 100 ana desteğine çok yakın (+1.0 Puan)")

        ai_puan = min(10.0, max(0.0, round(ai_puan, 1))) 
        doluluk_yuzdesi = int((ai_puan / 10.0) * 100)
        
        st.markdown("<div class='ai-score-box'>", unsafe_allow_html=True)
        st.markdown(f"<h2>🤖 YAPAY ZEKA HİBRİT KARAR MOTORU (ÖZET RAPOR)</h2>", unsafe_allow_html=True)
        st.markdown(f"<h1>{ai_puan} <span style='font-size: 1.5rem; color: #AAAAAA;'>/ 10</span></h1>", unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style="width: 100%; background-color: #111111; height: 14px; border-radius: 7px; margin-bottom: 20px; box-shadow: inset 0 1px 3px rgba(0,0,0,0.5);">
            <div style="width: {doluluk_yuzdesi}%; background: linear-gradient(90deg, #FF8C00 0%, #FFD700 100%); height: 100%; border-radius: 7px; transition: width 1s ease-in-out; box-shadow: 0 0 10px rgba(255, 215, 0, 0.4);"></div>
        </div>
        """, unsafe_allow_html=True)
        
        if rsi_val > 75 or son_fiyat >= son_ust:
            st.error("🚨 **SİSTEM UYARISI: KÂR ALMA / SATIŞ BÖLGESİ!**")
            emir_notu = "Aşırı alım ve trend kanalı tavan bölgesine ulaşıldı. Mevcut pozisyonlarda kar realizasyonu veya sıkı stop takibi önerilir. Yeni alım için risklidir."
        elif ai_puan >= 7.5:
            st.success("🟢 **KUSURSUZ FIRSAT (GÜÇLÜ ALIM):**")
            emir_notu = "Hem mali rasyolar hem de stratejik teknik destekler mükemmel bir örtüşme sinyali veriyor. Güçlü alım ve orta vadeli yatırım pozisyonu için ideal bölge."
        elif ai_puan >= 5.0:
            st.warning("🟡 **POTANSİYEL (İZLEME VE KADEMELİ ALIM):**")
            emir_notu = "Sistem belirli riskler barındırmakla birlikte genel görünümü olumlu değerlendiriyor. Destek seviyelerine doğru çekilmelerde kademeli alım stratejisi uygulanabilir."
        else:
            st.error("🔴 **RİSKLİ BÖLGE (UZAK DUR):**")
            emir_notu = "Zayıf kârlılık, yüksek çarpanlar ve negatif trend baskısı mevcut. Teknik kırılım netleşene ve mali rasyolar düzelene kadar izlemede kalınmalıdır."
        st.markdown("</div>", unsafe_allow_html=True)

        # ---------------------------------------------------------------------------------
        # YAPAY ZEKA STRATEJİK KOMUTA EMİR NOTLARI PANELİ
        # ---------------------------------------------------------------------------------
        st.markdown("### 🧠 YAPAY ZEKA STRATEJİK KOMUTA EMİR NOTLARI")
        st.markdown("<div class='ai-comment-box'>", unsafe_allow_html=True)
        st.markdown(f"**🎯 Stratejik Sistem Özeti:** Hissede anlık olarak hesaplanan hibrit otonom skor 10 üzerinden **{ai_puan}** puan seviyesindedir. {sektor_durum_metni}")
        st.markdown(f"**📋 Algoritma Analiz Gerekçeleri:**")
        for g in gerekceler:
            st.markdown(f"- {g}")
        st.markdown(f"**🛡️ Komuta Merkezi Strateji Emri:** {emir_notu}")
        st.markdown("</div>", unsafe_allow_html=True)

        # ANA PİYASA DURUMU (XU100 & XU030)
        st.markdown("---")
        st.markdown("## 🌍 ANA PİYASA DURUMU (BIST 100 & 30)")
        
        @st.cache_data(ttl=60)
        def get_index_data(symbol):
            data = yf.download(symbol, period="6mo", interval="1d", progress=False)
            if data.empty: return pd.DataFrame()
            if isinstance(data.columns, pd.MultiIndex): data.columns = data.columns.get_level_values(0)
            data.columns = [str(c).strip().capitalize() for c in data.columns]
            
            data['EMA21'] = data['Close'].ewm(span=21, adjust=False).mean()
            data['EMA50'] = data['Close'].ewm(span=50, adjust=False).mean()
            
            delta_idx = data['Close'].diff()
            gain_idx = (delta_idx.where(delta_idx > 0, 0)).rolling(window=14).mean()
            loss_idx = (-delta_idx.where(delta_idx < 0, 0)).rolling(window=14).mean()
            rs_idx = gain_idx / (loss_idx + 1e-9)
            data['RSI'] = 100 - (100 / (1 + rs_idx))
            return data

        idx_col1, idx_col2 = st.columns(2)
        with idx_col1:
            st.subheader("BIST 100 (XU100)")
            df_x100 = get_index_data("XU100.IS")
            if not df_x100.empty:
                son_100 = df_x100['Close'].iloc[-1].item()
                onceki_100 = df_x100['Close'].iloc[-2].item()
                degisim_100 = ((son_100 - onceki_100) / onceki_100) * 100
                st.metric("Puan", f"{son_100:.2f}", f"{degisim_100:.2f}%")
                fig100 = go.Figure(go.Scatter(x=df_x100.index[-60:], y=df_x100['Close'].tail(60), line=dict(color='#1f77b4', width=3)))
                fig100.update_layout(height=120, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_visible=False, yaxis_visible=False)
                st.plotly_chart(fig100, use_container_width=True)

        with idx_col2:
            st.subheader("BIST 30 (XU030)")
            df_x030 = get_index_data("XU030.IS")
            if not df_x030.empty:
                son_30 = df_x030['Close'].iloc[-1].item()
                onceki_30 = df_x030['Close'].iloc[-2].item()
                degisim_30 = ((son_30 - onceki_30) / onceki_30) * 100
                st.metric("Puan", f"{son_30:.2f}", f"{degisim_30:.2f}%")
                fig30 = go.Figure(go.Scatter(x=df_x030.index[-60:], y=df_x030['Close'].tail(60), line=dict(color='#9C27B0', width=3)))
                fig30.update_layout(height=120, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_visible=False, yaxis_visible=False)
                st.plotly_chart(fig30, use_container_width=True)

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
# ÇEKİRDEK 2: FULL HİBRİT RADAR
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
                inf = t.info
                if hist.empty: continue
                skor = 0
                son_fiyat = hist['Close'].iloc[-1].item()
                
                # SAF PANDAS TEKNİK METRİKLER (RADAR)
                ema21 = hist['Close'].ewm(span=21, adjust=False).mean().iloc[-1].item()
                
                delta_r = hist['Close'].diff()
                gain_r = (delta_r.where(delta_r > 0, 0)).rolling(window=14).mean()
                loss_r = (-delta_r.where(delta_r < 0, 0)).rolling(window=14).mean()
                rs_r = gain_r / (loss_r + 1e-9)
                rsi = (100 - (100 / (1 + rs_r))).iloc[-1].item()
                
                if son_fiyat > ema21: skor += 1
                if 30 < rsi < 65: skor += 1
                fk = inf.get('trailingPE', 100)
                if fk < 15: skor += 1
                pddd = inf.get('priceToBook', 100)
                if pddd < 3: skor += 1
                roe = inf.get('returnOnEquity', 0)
                if roe is not None and roe > 0.20: skor += 1

                sonuclar.append({
                    "Hisse": kod.replace(".IS", ""), "Fiyat": round(son_fiyat, 2),
                    "F/K": round(fk, 2) if fk != 100 else "N/A", "PD/DD": round(pddd, 2) if pddd != 100 else "N/A",
                    "ROE (%)": round(roe*100, 2) if roe else "N/A", "RSI": round(rsi, 2), "Hibrit Skor": skor,
                    "Sistem Notu": "👑 ŞAMPİYON" if skor >= 4 else ("🟢 GÜÇLÜ" if skor == 3 else ("🟡 MAKUL" if skor == 2 else "⚪ İZLE"))
                })
                time.sleep(0.1)
            except: pass
            ilerleme.progress((i + 1) / len(bist100_tam_liste))
        df_sonuc = pd.DataFrame(sonuclar).sort_values(by="Hibrit Skor", ascending=False).reset_index(drop=True)
        st.session_state.hibrit_tablo_full = df_sonuc
        df_sonuc.to_csv("son_tarama_kaydi.csv", index=False)
        durum_m.success("✅ Kaydedildi!")

    if not st.session_state.hibrit_tablo_full.empty:
        def renk_motoru(val):
            if val == "👑 ŞAMPİYON": return 'background-color: #FFD700; color: black; font-weight: bold;'
            if val == "🟢 GÜÇLÜ": return 'background-color: #C8E6C9; color: black; font-weight: bold;'
            return ''
        styled_df = st.session_state.hibrit_tablo_full.style.map(renk_motoru, subset=['Sistem Notu'])
        st.dataframe(styled_df, use_container_width=True, height=800)

# =================================================================================
# ÇEKİRDE• 3: FOREX & KÜRESEL PİYASALAR (ÇİFT YÖNLÜ SİSTEM)
# =================================================================================
elif calisma_modu == "Forex & Küresel Piyasalar (Çift Yönlü)":
    st_autorefresh(interval=60000, key="global_forex_refresh")
    st.markdown("## 🌐 ÇİFT YÖNLÜ OTONOM FOREX KOMUTA MERKEZİ")
    
    secilen_forex_adi = st.selectbox("Analiz Edilecek Küresel Enstrüman:", list(forex_assets.keys()))
    forex_ticker = forex_assets[secilen_forex_adi]
    
    try:
        df_fx = yf.download(tickers=forex_ticker, period="1mo", interval="1h", progress=False)
    except:
        df_fx = pd.DataFrame()
        
    if not df_fx.empty and len(df_fx) > 25:
        if isinstance(df_fx.columns, pd.MultiIndex): df_fx.columns = df_fx.columns.get_level_values(0)
        df_fx.columns = [str(c).strip().capitalize() for c in df_fx.columns]
        
        # 1. Kristal Box Hesaplamaları (Donchian)
        df_fx['box_ust'] = df_fx['High'].rolling(window=20).max()
        df_fx['box_alt'] = df_fx['Low'].rolling(window=20).min()
        df_fx['box_orta'] = (df_fx['box_ust'] + df_fx['box_alt']) / 2
        
        # 2. SAF PANDAS TEKNİK İNDİKATÖRLER (FOREX)
        df_fx['EMA21'] = df_fx['Close'].ewm(span=21, adjust=False).mean()
        df_fx['EMA50'] = df_fx['Close'].ewm(span=50, adjust=False).mean()
        
        # SAF PANDAS FOREX RSI
        delta_fx = df_fx['Close'].diff()
        gain_fx = (delta_fx.where(delta_fx > 0, 0)).rolling(window=14).mean()
        loss_fx = (-delta_fx.where(delta_fx < 0, 0)).rolling(window=14).mean()
        rs_fx = gain_fx / (loss_fx + 1e-9)
        df_fx['RSI'] = 100 - (100 / (1 + rs_fx))
        
        # SAF PANDAS ATR (TRUE RANGE ORTALAMASI)
        high_low = df_fx['High'] - df_fx['Low']
        high_cp = (df_fx['High'] - df_fx['Close'].shift()).abs()
        low_cp = (df_fx['Low'] - df_fx['Close'].shift()).abs()
        tr = pd.concat([high_low, high_cp, low_cp], axis=1).max(axis=1)
        df_fx['ATR'] = tr.rolling(window=14).mean()
        
        son_fiyat = float(df_fx['Close'].iloc[-1].item())
        atr_val = float(df_fx['ATR'].iloc[-1].item())
        rsi_val = float(df_fx['RSI'].iloc[-1].item())
        b_ust = float(df_fx['box_ust'].iloc[-2].item())
        b_alt = float(df_fx['box_alt'].iloc[-2].item())
        ema21 = float(df_fx['EMA21'].iloc[-1].item())
        ema50 = float(df_fx['EMA50'].iloc[-1].item())
        
        # 3. ÇİFT YÖNLÜ KARAR MOTORU (SKORLAMA & YÖN TAYİNİ)
        long_skor = 0.0
        short_skor = 0.0
        nedenler = []
        
        # Kristal Box Kırılım Analizi
        if son_fiyat > b_ust:
            long_skor += 4.0
            nedenler.append("🟩 KRİSTAL BOX: Üst band yukarı yönlü kırıldı (Long +4)")
        elif son_fiyat < b_alt:
            short_skor += 4.0
            nedenler.append("🟥 KRİSTAL BOX: Alt band aşağı yönlü kırıldı (Short +4)")
        else:
            long_skor += 1.0
            short_skor += 1.0
            nedenler.append("🟨 KRİSTAL BOX: Fiyat kutu içinde konsolide oluyor (Nötr +1)")
            
        # Gann / EMA Trend Yapısı Analizi
        if son_fiyat > ema21 and ema21 > ema50:
            long_skor += 3.5
            nedenler.append("🟩 GANN/TREND: EMA'lar boğa diziliminde ve fiyat üstünde (Long +3.5)")
        elif son_fiyat < ema21 and ema21 < ema50:
            short_skor += 3.5
            nedenler.append("🟥 GANN/TREND: EMA'lar ayı diziliminde ve fiyat altında (Short +3.5)")
        else:
            nedenler.append("🟨 GANN/TREND: Hareketli ortalamalar kararsız bölgede")
            
        # RSI / Momentum Analizi
        if 50 < rsi_val < 70:
            long_skor += 2.5
            nedenler.append("🟩 MOMENTUM: RSI yükseliş trendini destekliyor (Long +2.5)")
        elif 30 < rsi_val <= 50:
            short_skor += 2.5
            nedenler.append("🟥 MOMENTUM: RSI düşüş eğilimini destekliyor (Short +2.5)")
        elif rsi_val >= 70:
            short_skor += 1.5
            nedenler.append("⚠️ MOMENTUM: Aşırı Alım! Short yönlü dönüş tetiklenebilir (Short +1.5)")
        elif rsi_val <= 30:
            long_skor += 1.5
            nedenler.append("⚠️ MOMENTUM: Aşırı Satım! Long yönlü tepki tetiklenebilir (Long +1.5)")

        # Yön ve Strateji Belirleme
        if long_skor >= 7.0 and long_skor >= short_skor:
            strateji_yönü = "LONG (YUKARI)"
            ana_skor = long_skor
            durum_color = "#2ECC71"
            durum_msg = "🚀 GÜÇLÜ BOĞA - YUKARI İŞLEM AÇILABİLİR"
            sl_noktasi = son_fiyat - (atr_val * 1.5)
            tp_noktasi = son_fiyat + (atr_val * 3.0)
        elif short_skor >= 7.0 and short_skor > long_skor:
            strateji_yönü = "SHORT (AŞAĞI)"
            ana_skor = short_skor
            durum_color = "#E74C3C"
            durum_msg = "💥 GÜÇLÜ AYI - AŞAĞI (AÇIĞA SATIŞ) İŞLEM UYGUN"
            sl_noktasi = son_fiyat + (atr_val * 1.5)
            tp_noktasi = son_fiyat - (atr_val * 3.0)
        else:
            strateji_yönü = "NÖTR (İZLE)"
            ana_skor = max(long_skor, short_skor)
            durum_color = "#F1C40F"
            durum_msg = "🟡 TEST BÖLGESİ - YÖN BELİRSİZ, KIRILIM BEKLEYİN"
            sl_noktasi = son_fiyat - (atr_val * 2.0)
            tp_noktasi = son_fiyat + (atr_val * 2.0)

        # Savaş Kartı Gösterimi
        st.markdown(f"""
            <div style="background-color: {durum_color}; padding: 25px; border-radius: 15px; text-align: center; margin-bottom: 25px; box-shadow: 0 4px 15px rgba(0,0,0,0.15);">
                <h1 style="color: #FFFFFF !important; border: none; margin: 0; font-size: 2.2rem;">{secilen_forex_adi} // STRATEJİ: {strateji_yönü}</h1>
                <h3 style="color: #FFFFFF !important; border: none; margin: 8px 0 0 0; font-weight: 800;">{durum_msg} (Skor: {ana_skor:.1f}/10)</h3>
            </div>
        """, unsafe_allow_html=True)

        # METRIC SENSÖRLERİ
        f1, f2, f3, f4 = st.columns(4)
        f1.metric("ANLIK FİYAT", f"{son_fiyat:.4f}")
        f2.metric("OYNK_ALANI (ATR)", f"{atr_val:.4f}")
        f3.metric("🎯 OTONOM TP (KAR AL)", f"{tp_noktasi:.4f}")
        f4.metric("🛑 OTONOM SL (ZARAR KES)", f"{sl_noktasi:.4f}")

        # PANEL YERLEŞİMİ
        sol_p, sag_p = st.columns([1, 2])
        
        with sol_p:
            st.markdown("### 🧠 Çift Yönlü Skor Detayları")
            st.info(f"🟢 **Long Algoritma Skoru:** {long_skor:.1f} / 10")
            st.info(f"🔴 **Short Algoritma Skoru:** {short_skor:.1f} / 10")
            
            st.markdown("#### 🔍 Sinyal Gerekçeleri")
            for neden in nedenler:
                st.write(f"- {neden}")
                
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
            
            if strateji_yönü != "NÖTR (İZLE)":
                fig_fx.add_trace(go.Scatter(x=[df_fx.index[-20], df_fx.index[-1]], y=[tp_noktasi, tp_noktasi], line=dict(color='#2ECC71', width=2.5), name="Hedef (TP)"), row=1, col=1)
                fig_fx.add_trace(go.Scatter(x=[df_fx.index[-20], df_fx.index[-1]], y=[sl_noktasi, sl_noktasi], line=dict(color='#E74C3C', width=2.5), name="Risk Sınırı (SL)"), row=1, col=1)
            
            fig_fx.add_trace(go.Scatter(x=df_fx.index, y=df_fx['RSI'], line=dict(color='#16A085', width=1.5), name="RSI"), row=2, col=1)
            
            # Convert timezone-naive timestamp limits for plotly line plotting safely
            t_start = df_fx.index[0]
            t_end = df_fx.index[-1]
            fig_fx.add_trace(go.Scatter(x=[t_start, t_end], y=[70, 70], line=dict(color='rgba(231, 76, 60, 0.5)', width=1, dash='dot'), showlegend=False), row=2, col=1)
            fig_fx.add_trace(go.Scatter(x=[t_start, t_end], y=[30, 30], line=dict(color='rgba(46, 204, 113, 0.5)', width=1, dash='dot'), showlegend=False), row=2, col=1)
            
            fig_fx.update_layout(xaxis_rangeslider_visible=False, height=650, template="plotly_white", margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig_fx, use_container_width=True)
    else:
        st.error("Küresel piyasa verileri çekilemedi. Bağlantınızı kontrol edin.")
