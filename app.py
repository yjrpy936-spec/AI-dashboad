import os
import google.genai as genai
import pandas as pd
import streamlit as st
import yfinance as yf

# --- ページ基本設定 ---
st.set_page_config(
    page_title="Ultimate AI & Sentiment Portfolio Dashboard",
    page_icon="⚡",
    layout="wide",
)

# --- 1. APIキーの自動取得 ---
gemini_key = ""
if "GEMINI_API_KEY" in st.secrets:
    gemini_key = st.secrets["GEMINI_API_KEY"]
else:
    gemini_key = st.sidebar.text_input(
        "Gemini API Key",
        type="password",
        help="※StreamlitのSecretsに設定すると自動読み込みされます",
    )

st.title("⚡ 次世代AI・統合型クオンツ投資ダッシュボード")
st.caption(
    "※免責事項: 本ツールは市場心理・オプション・AI分析による情報提供を目的としており、投資助言を行うものではありません。"
)

# --- 2. ユーザー設定（監視銘柄 & 保有データ） ---
st.sidebar.header("⚙️ ポートフォリオ設定")

default_tickers = "NVDA, AMZN, META, GOOGL"
user_input = st.sidebar.text_area(
    "監視銘柄（カンマ区切り）",
    value=st.query_params.get("tickers", default_tickers),
    help="例: NVDA, AAPL, 7203.T, BTC-USD",
)
ticker_list = [t.strip().upper() for t in user_input.split(",") if t.strip()]
st.query_params["tickers"] = ", ".join(ticker_list)

st.sidebar.subheader("💰 保有数量・平均取得単価（任意）")
holding_data = {}
for ticker in ticker_list:
    with st.sidebar.expander(f"{ticker} の保有詳細"):
        shares = st.number_input(
            f"{ticker} 保有株数", min_value=0.0, value=0.0, step=1.0, key=f"s_{ticker}"
        )
        avg_cost = st.number_input(
            f"{ticker} 取得単価",
            min_value=0.0,
            value=0.0,
            step=0.1,
            key=f"c_{ticker}",
        )
        if shares > 0:
            holding_data[ticker] = {"shares": shares, "avg_cost": avg_cost}

# --- 3. マクロ指標の取得 ---
@st.cache_data(ttl=600)
def get_macro_data():
    try:
        us10y = yf.Ticker("^TNX").history(period="2d")["Close"].iloc[-1]
        usdjpy = yf.Ticker("JPY=X").history(period="2d")["Close"].iloc[-1]
        vix = yf.Ticker("^VIX").history(period="2d")["Close"].iloc[-1]
        nasdaq = yf.Ticker("^IXIC").history(period="2d")["Close"].iloc[-1]
        return us10y, usdjpy, vix, nasdaq
    except Exception:
        return None, None, None, None

us10y, usdjpy, vix, nasdaq = get_macro_data()

# マクロ指標の常時表示
if us10y:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("米10年債利回り (US10Y)", f"{us10y:.2f}%")
    m2.metric("ドル円 (USD/JPY)", f"￥{usdjpy:.2f}")
    m3.metric("VIX (恐怖指数)", f"{vix:.2f}")
    m4.metric("NASDAQ総合", f"{nasdaq:,.0f}")

st.divider()

# --- 4. 共通データ収集（価格、RSI、オプションIV等） ---
summary_text_for_ai = ""
stock_metrics = {}

for ticker in ticker_list:
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="30d")
        if len(hist) >= 14:
            latest = hist["Close"].iloc[-1]
            prev = hist["Close"].iloc[-2]
            pct = ((latest - prev) / prev) * 100

            # RSI計算
            delta = hist["Close"].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs)).iloc[-1]

            # オプションIV取得
            iv_avg = 0
            pcr = 0
            try:
                expirations = stock.options
                if expirations:
                    opt_chain = stock.option_chain(expirations[0])
                    calls, puts = opt_chain.calls, opt_chain.puts
                    call_iv = calls['impliedVolatility'].mean() if not calls.empty else 0
                    put_iv = puts['impliedVolatility'].mean() if not puts.empty else 0
                    iv_avg = ((call_iv + put_iv) / 2) * 100
                    total_call_vol = calls['volume'].sum() if not calls.empty else 1
                    total_put_vol = puts['volume'].sum() if not puts.empty else 0
                    pcr = total_put_vol / total_call_vol if total_call_vol > 0 else 0
            except Exception:
                pass

            # 損益計算
            pnl_val, pnl_pct = 0, 0
            currency_symbol = "￥" if ticker.endswith(".T") else "$"
            if ticker in holding_data:
                sh = holding_data[ticker]["shares"]
                ac = holding_data[ticker]["avg_cost"]
                if ac > 0:
                    pnl_val = (sh * latest) - (sh * ac)
                    pnl_pct = (pnl_val / (sh * ac)) * 100

            stock_metrics[ticker] = {
                "latest": latest, "pct": pct, "rsi": rsi, "iv": iv_avg, "pcr": pcr, "pnl_val": pnl_val, "pnl_pct": pnl_pct
            }
            summary_text_for_ai += f"・{ticker}: 終値={latest:.2f}, 前日比={pct:+.2f}%, RSI={rsi:.1f}, オプションIV={iv_avg:.1f}%, PCR={pcr:.2f}, 含み損益={currency_symbol}{pnl_val:,.1f}({pnl_pct:+.2f}%)\n"
    except Exception:
        pass

# --- 5. タブによる機能の完全統合 ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 総合ダッシュボード & オプション", 
    "🧠 行動ファイナンス診断", 
    "⚡ What-if ストレステスト", 
    "🔗 隠れ相関リスク", 
    "📝 決算・行間分析"
])

# --- TAB 1: 総合ダッシュボード ---
with tab1:
    st.subheader("📊 Myポートフォリオ & 市場センチメント")
    cols = st.columns(min(len(ticker_list), 4) if ticker_list else 1)
    for idx, ticker in enumerate(ticker_list):
        c = cols[idx % 4]
        if ticker in stock_metrics:
            m = stock_metrics[ticker]
            cs = "￥" if ticker.endswith(".T") else "$"
            c.metric(f"{ticker} (RSI:{m['rsi']:.0f})", f"{cs}{m['latest']:,.2f}", f"{m['pct']:+.2f}%")
            if m['iv'] > 0:
                c.caption(f"オプションIV: {m['iv']:.1f}% (PCR: {m['pcr']:.2f})")
            if ticker in holding_data and holding_data[ticker]['avg_cost'] > 0:
                c.caption(f"含み損益: {cs}{m['pnl_val']:,.1f} ({m['pnl_pct']:+.2f}%)")

    st.divider()
    if st.button("総合AI市場レポートを生成する", type="primary"):
        if not gemini_key:
            st.warning("⚠️ APIキーが設定されていません。")
        else:
            with st.spinner("AIがマクロ、RSI、オプション市場を統合分析中..."):
                try:
                    client = genai.Client(api_key=gemini_key)
                    prompt = f"""
プロのクオンツ・アナリストとして、以下のマクロとポートフォリオデータ（価格、RSI、オプションIV）を分析し、過熱感やリスクを日本語でレポートしてください（400文字程度）。
【マクロ】米10年債:{us10y}%, ドル円:{usdjpy}円, VIX:{vix}, NASDAQ:{nasdaq}
【ポートフォリオ】\n{summary_text_for_ai}
"""
                    res = client.models.generate_content(model="gemini-3.8-flash", contents=prompt)
                    st.success("分析完了")
                    st.markdown(res.text)
                except Exception as e:
                    st.error(f"エラー: {e}")

# --- TAB 2: 行動ファイナンス診断 ---
with tab2:
    st.subheader("🧠 行動ファイナンスAI（心理バイアス・カウンセラー）")
    st.markdown("現在の相場環境とあなたの保有状況から、**『正常性バイアス』『プロスペクト理論（損切りできない）』『FOMO（焦り）』**などの心理的罠にはまっていないかをAIが診断します。")
    if st.button("心理バイアスを診断する"):
        if not gemini_key:
            st.warning("⚠️ APIキーを設定してください。")
        else:
            with st.spinner("行動ファイナンスの観点から心理状態を診断中..."):
                try:
                    client = genai.Client(api_key=gemini_key)
                    prompt = f"""
あなたは行動ファイナンスに精通した投資心理カウンセラーです。以下のユーザーの保有状況と市場データに基づき、個人投資家が陥りがちな心理的バイアス（利益が出たらすぐに売りたい「処分効果」、損切りできない心理、群集心理に流されるFOMOなど）の観点から、客観的で厳しい、しかし愛のある警告とアドバイスを行ってください。
【データ】\n{summary_text_for_ai}
【マクロ】VIX: {vix}, 米10年債: {us10y}%
"""
                    res = client.models.generate_content(model="gemini-3.8-flash", contents=prompt)
                    st.success("診断完了")
                    st.markdown(res.text)
                except Exception as e:
                    st.error(f"エラー: {e}")

# --- TAB 3: What-if ストレステスト ---
with tab3:
    st.subheader("⚡ What-if シナリオ・ストレステスト")
    st.markdown("「もしも市場環境が激変したら、私の資産はどうなるか？」をシミュレーションします。")
    
    stress_type = st.selectbox(
        "シミュレーションするシナリオを選択",
        [
            "シナリオA: 米10年債利回りが 4.8% に急騰 & NASDAQ 5%下落",
            "シナリオB: VIX（恐怖指数）が 30 を突破するパニック相場",
            "シナリオC: ドル円が 140円台へ急激な円高進行"
        ]
    )
    
    if st.button("ストレステストを実行"):
        if not gemini_key:
            st.warning("⚠️ APIキーを設定してください。")
        else:
            with st.spinner("AIがストレステストの影響度を計算中..."):
                try:
                    client = genai.Client(api_key=gemini_key)
                    prompt = f"""
あなたはリスク管理の専門家です。以下のポートフォリオに対し、選択されたシナリオ（{stress_type}）が発動した場合、それぞれの銘柄や全体資産にどのような致命的ダメージ、あるいは恩恵があるかを推算し、具体的な防衛策を提案してください。
【ポートフォリオ】\n{summary_text_for_ai}
"""
                    res = client.models.generate_content(model="gemini-3.8-flash", contents=prompt)
                    st.success("ストレステスト完了")
                    st.markdown(res.text)
                except Exception as e:
                    st.error(f"エラー: {e}")

# --- TAB 4: 隠れ相関リスク診断 ---
with tab4:
    st.subheader("🔗 隠れ相関リスク診断（本当の分散の確認）")
    st.markdown("「分散投資しているつもりなのに、実は金利やマクロ環境に対して全く同じ動きをする銘柄ばかり持っていないか」をAIがチェックします。")
    if st.button("相関リスクを診断する"):
        if not gemini_key:
            st.warning("⚠️ APIキーを設定してください。")
        else:
            with st.spinner("銘柄間の隠れ相関を分析中..."):
                try:
                    client = genai.Client(api_key=gemini_key)
                    prompt = f"""
あなたはクオンツ・ポートフォリオマネージャーです。以下の監視・保有銘柄の組み合わせに、金利上昇や景気後退ショック時の「隠れ相関リスク（実は同じ方向へ連鎖的に崩れるリスク）」がないか分析し、真の分散効果を高めるためのアドバイスを与えてください。
【銘柄リスト】: {ticker_list}
【データ】\n{summary_text_for_ai}
"""
                    res = client.models.generate_content(model="gemini-3.8-flash", contents=prompt)
                    st.success("相関分析完了")
                    st.markdown(res.text)
                except Exception as e:
                    st.error(f"エラー: {e}")

# --- TAB 5: 決算・行間分析 ---
with tab5:
    st.subheader("📝 英語圏決算・10-Kの『行間を読む』AI分析")
    st.markdown("米国株の決算発表やカンファレンスコール（文字起こし）の英文をここに貼り付けると、**『経営陣がどこをごまかしているか、トーンが弱気になっていないか』**をプロの視点で暴きます。")
    
    earning_text_input = st.text_area("決算ニュース、英語のトランスクリプト、プレスリリース等を貼り付け", height=150)
    
    if st.button("行間と本音を分析する"):
        if not gemini_key:
            st.warning("⚠️ APIキーを設定してください。")
        elif not earning_text_input.strip():
            st.warning("⚠️ 分析するテキストを入力してください。")
        else:
            with st.spinner("AIが経営陣のトーンと行間を解析中..."):
                try:
                    client = genai.Client(api_key=gemini_key)
                    prompt = f"""
あなたは機関投資家のベテラン・アナリストです。以下の企業決算や経営陣の発言（英文または日本語）の「行間」を読み解く、表向きの良いニュースの裏に隠されたリスク、経営陣のトーンの変化（弱気なニュアンスなど）、個人投資家が見落としがちな本音を鋭く分析してください。
【入力テキスト】
{earning_text_input}
"""
                    res = client.models.generate_content(model="gemini-3.8-flash", contents=prompt)
                    st.success("行間分析完了")
                    st.markdown(res.text)
                except Exception as e:
                    st.error(f"エラー: {e}")
