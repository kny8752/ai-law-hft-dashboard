import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime

def generate_sample_data():
    np.random.seed(42)
    time_index = pd.date_range(start='2026-08-17 09:00:00', periods=100, freq='100L')
    df = pd.DataFrame({
        'timestamp': time_index,
        'price': 50000 + np.cumsum(np.random.randn(100) * 50),
        'order_qty': np.random.randint(1000, 50000, 100),
        'canceled_qty': np.random.randint(500, 48000, 100),
        'cancel_time_gap_ms': np.random.randint(10, 200, 100),
        'buy_vol': np.random.randint(1000, 50000, 100),
        'sell_vol': np.random.randint(1000, 50000, 100),
        'current_vol': np.random.randint(10000, 80000, 100),
        'avg_vol_5min': 20000,
        'position_reversed': False
    })
    # 모멘텀 점화 및 스푸핑 패턴 주입 (심사위원 테스트용)
    df.loc[70:75, 'buy_vol'] = df.loc[70:75, 'buy_vol'] * 5
    df.loc[70:75, 'current_vol'] = df.loc[70:75, 'current_vol'] * 4
    df.loc[75, 'position_reversed'] = True
    df.loc[20:25, 'canceled_qty'] = df.loc[20:25, 'order_qty'] * 0.95
    df.loc[20:25, 'cancel_time_gap_ms'] = 30
    return df

class MarketDisruptionRuleEngine:
    def __init__(self, df): self.df = df.copy()
    def detect_spoofing(self, cancel_ratio_threshold, time_gap_ms):
        self.df['cancel_ratio'] = self.df['canceled_qty'] / self.df['order_qty']
        return self.df[(self.df['cancel_ratio'] >= cancel_ratio_threshold) & (self.df['cancel_time_gap_ms'] <= time_gap_ms)]
    def detect_momentum_ignition(self, asymmetry_threshold, vol_surge_multiplier):
        self.df['asymmetry_index'] = abs(self.df['buy_vol'] - self.df['sell_vol']) / (self.df['buy_vol'] + self.df['sell_vol'])
        self.df['is_vol_surge'] = self.df['current_vol'] > (self.df['avg_vol_5min'] * vol_surge_multiplier)
        return self.df[(self.df['asymmetry_index'] >= asymmetry_threshold) & (self.df['is_vol_surge']) & (self.df['position_reversed'] == True)]

def run_dashboard():
    st.set_page_config(page_title="시장질서 교란행위 감지 시스템", layout="wide")
    st.title("⚖️ HFT 시장질서 교란행위 감지 및 과징금 산정 시스템")
    st.markdown("**[AI와 법 논문대회 출품작]** 자본시장법 제178조의2 제2항 제5호(신설) 실무 적용 프로토타입")
    
    with st.sidebar:
        st.header("📊 데이터 업로드")
        st.info("👇 심사위원 시연용 샘플 파일을 받아 아래에 업로드해 보세요.")
        sample_csv = generate_sample_data().to_csv(index=False).encode('utf-8')
        st.download_button("📥 조작 의심 샘플 CSV 다운로드", data=sample_csv, file_name="sample_hft_log.csv", mime="text/csv")
        
        uploaded_file = st.file_uploader("호가/체결 데이터 (CSV)", type=['csv'])
        st.divider()
        st.subheader("시행령 판단기준 임계치 조정")
        cancel_ratio_th = st.slider("가목: 취소율 기준 (%)", 50.0, 99.9, 90.0, 0.1) / 100
        time_gap_th = st.slider("다목: 제출-취소 간격 (ms)", 1, 500, 50, 1)
        asym_th = st.slider("라목: 비대칭성 지수", 0.5, 1.0, 0.8, 0.05)
        vol_surge_th = st.slider("마목: 거래량 급증 (배)", 1.5, 10.0, 3.0, 0.5)

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
    else:
        df = generate_sample_data()

    engine = MarketDisruptionRuleEngine(df)
    spoofing_cases = engine.detect_spoofing(cancel_ratio_th, time_gap_th)
    ignition_cases = engine.detect_momentum_ignition(asym_th, vol_surge_th)
    base_fine = (len(spoofing_cases) * 50000000) + (len(ignition_cases) * 150000000)

    tab1, tab2, tab3 = st.tabs(["📈 실시간 감시 대시보드", "📝 행정처분 통지서 및 집행", "🔍 법령-알고리즘 XAI 매핑"])

    with tab1:
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("총 분석 틱(Tick)", f"{len(df):,} 건")
        kpi2.metric("제1호 (허수성) 적발", f"{len(spoofing_cases)} 건", delta_color="inverse")
        kpi3.metric("제5호 (모멘텀 점화) 적발", f"{len(ignition_cases)} 건", delta_color="inverse")
        kpi4.metric("💰 산정 과징금액", f"{base_fine / 100000000:.1f} 억원")

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Scatter(x=df['timestamp'], y=df['price'], name="체결가", line=dict(color='black')), secondary_y=True)
        fig.add_trace(go.Bar(x=df['timestamp'], y=df['buy_vol'], name="매수 호가잔량", marker_color='rgba(255, 99, 132, 0.6)'), secondary_y=False)
        fig.add_trace(go.Bar(x=df['timestamp'], y=-df['sell_vol'], name="매도 호가잔량", marker_color='rgba(54, 162, 235, 0.6)'), secondary_y=False)
        
        if not ignition_cases.empty:
            fig.add_trace(go.Scatter(x=ignition_cases['timestamp'], y=ignition_cases['price'], mode='markers', name='제5호 위반', marker=dict(color='red', size=12, symbol='x')), secondary_y=True)
        
        fig.update_layout(height=400, margin=dict(l=0, r=0, t=30, b=0), barmode='relative')
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("과징금 부과 사전통지서 및 즉각 집행")
        st.markdown(f"""
        <div style="padding: 30px; border: 2px solid #333; background-color: #f9f9f9;">
            <h2 style="text-align: center;">과징금 부과 사전통지서</h2>
            <br>
            <p><b>처분의 원인이 되는 법령:</b> 자본시장법 제178조의2 및 동법 시행령 제○○조</p>
            <p><b>위반 사실:</b> 신설 제5호(알고리즘 추세 조작) {len(ignition_cases)}건 적발</p>
            <p><b>부과 예정 과징금액:</b> 금 <b>{base_fine:,}</b> 원</p>
            <h3 style="text-align: center;">금융위원회 위원장 (관인생략)</h3>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⚖️ [원클릭 집행] 위 사전통지서를 해당 기관에 전자 발송 및 거래소 이상거래망(EXIGHT)에 등록", use_container_width=True, type="primary"):
            st.success("✅ **[집행 완료]** 자본시장법 제178조의2 위반에 따른 행정제재 절차가 시작되었습니다. (시뮬레이션)")
            st.info("증거 로그(XAI 매핑 결과)가 한국거래소 및 증권선물위원회로 안전하게 이관되었습니다.")

    with tab3:
        st.subheader("💡 알고리즘 코드 - 법령 매핑 (XAI)")
        col_law, col_code = st.columns(2)
        with col_law:
            st.info("**[신설] 시행령 라목**\n\n매수·매도 호가 규모의 비대칭성 및 반복성")
            st.info("**[신설] 제5호 본문**\n\n추세를 형성·강화한 후 반대방향으로 포지션을 전환")
        with col_code:
            st.code("df['asymmetry_index'] = abs(buy - sell) / (buy + sell)", language='python')
            st.code("(asymmetry_index >= 0.8) & (is_vol_surge) & (position_reversed)", language='python')

if __name__ == '__main__':
    run_dashboard()
