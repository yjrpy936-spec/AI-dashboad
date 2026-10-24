import os
import google.genai as genai
import requests
import streamlit as st
import yfinance as yf

# --- ページ基本設定 ---
st.set_page_config(
    page_title="AI Portfolio Dashboard", page_icon="📈", layout="wide"
)

# Gemini APIキーの取得（環境変数またはUIサイドバーから入力）
gemini_key = st.sidebar.text_input(
    "Gemini API Key",
    type="password",
    value=os.getenv("GEMINI_API_KEY", ""),
    help="Google AI Studioで発行した無料キーを入力",
)

st.title("📈 パーソナルAI市場診断ダッシュボード")
st.caption(
    "※免責事項: 本ツールは情報収集の効率化を目的としており、投資助言・勧誘を行うものではありません。"
)

# --- 1. ユーザー銘柄の選定・登録（URL/セッション保持） ---
st.sidebar.header("⚙️ My銘柄のカスタマイズ")

# デフォルト銘柄（初期状態）
default_tickers = "NVDA, AMZN, META, GOOGL"

# URLパラメータまたはセッション状態から読み込み
user_input = st.sidebar.text_area(
    "監視銘柄（カンマ区切り）",
    value=st.query_params.get("tickers", default_tickers),
    help="例: NVDA, AAPL, 7203.T (トヨタ), BTC-USD",
)

# 銘柄リストの生成
ticker_list = [t.strip().upper() for t in user_input.split(",") if t.strip()]

# URLパラメータの更新（ブックマーク共有や保存に対応）
st.query_params["tickers"] = ", ".join(ticker_list)

# --- 2. マクロ指標の表示（固定共通枠） ---
st.subheader("🌍 マクロ指標 & 市場センチメント")
macro_col1, macro_col2, macro_col3, macro_col4 = st.columns(4)


@st.cache_data(ttl=600)  # 10分キャッシュでAPI負荷低減
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
if us10y:
    macro_col1.metric("米10年債利回り", f"{us10y:.2f}%")
    macro_col2.metric("ドル円 (USD/JPY)", f"￥{usdjpy:.2f}")
    macro_col3.metric("VIX (恐怖指数)", f"{vix:.2f}")
    macro_col4.metric("NASDAQ総合", f"{nasdaq:,.0f}")

st.divider()

# --- 3. ユーザー登録銘柄のデータ取得 & 表示 ---
st.subheader("📊 Myポートフォリオ一覧")

summary_text_for_ai = ""
cols = st.columns(min(len(ticker_list), 4) if ticker_list else 1)

for idx, ticker in enumerate(ticker_list):
    col = cols[idx % 4]
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="5d")
        if len(hist) >= 2:
            latest = hist["Close"].iloc[-1]
            prev = hist["Close"].iloc[-2]
            pct = ((latest - prev) / prev) * 100

            col.metric(
                label=ticker,
                value=f"${latest:.2f}"
                if not ticker.endswith(".T")
                else f"￥{latest:.0f}",
                delta=f"{pct:+.2f}%",
            )

            summary_text_for_ai += f"・{ticker}: 終値={latest:.2f}, 前日比={pct:+.2f}%\n"
    except Exception as e:
        col.error(f"{ticker}: データ取得失敗")

st.divider()

# --- 広告枠の配置用スペース（例） ---
# st.components.v1.html("Google AdSense コードをここに挿入", height=100)

# --- 4. Gemini AIによるポートフォリオ一括分析 ---
st.subheader("🤖 AIによる本日の横断リスク＆トレンド要約")

if not gemini_key:
    st.info("👈 左側のサイドバーにGemini API Keyを入力すると、AI要約が実行されます。")
else:
    if st.button("AI市場要約を生成する", type="primary"):
        with st.spinner("AIが市場データとポートフォリオを分析中..."):
            try:
                client = genai.Client(api_key=gemini_key)

                prompt = f"""
あなたはプロの投資アナリストです。
現在のマクロ指標と、ユーザーが登録したポートフォリオの最新データに基づいて、短く的確な市況要約を作成してください。

【マクロ環境】
- 米10年債利回り: {us10y:.2f}%
- ドル円: {usdjpy:.2f}円
- VIX指数: {vix:.2f}

【ユーザーのポートフォリオデータ】
{summary_text_for_ai}

【出力フォーマット】
以下の3点を箇条書きで分かりやすく回答してください（合計300文字程度）：
1. **本日の市場環境まとめ**（金利・為替とハイテク株への影響）
2. **登録銘柄のリスク・好材料の検知**（急変動している銘柄や連動性）
3. **投資家の注意点**（アセット偏重リスクや本日の立ち回りアドバイス）
"""

                response = client.models.generate_content(
                    model="gemini-3.8-flash",
                    contents=prompt,
                )

                st.success("分析完了")
                st.markdown(response.text)

            except Exception as e:
                st.error(f"AI要約の生成中にエラーが発生しました: {e}")
