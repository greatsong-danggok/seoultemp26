import streamlit as st
import pandas as pd
import altair as alt
from datetime import date, timedelta

# ----------------------------------------------------
# 기본 설정
# ----------------------------------------------------
st.set_page_config(
    page_title="서울 역대 기온 랭킹",
    page_icon="🌡️",
    layout="centered",
)

CSV_PATH = "seoul.csv"  # 파일 경로 고정

# ----------------------------------------------------
# 스타일 (커스텀 CSS)
# ----------------------------------------------------
st.markdown(
    """
    <style>
    html, body, [class*="css"]  {
        font-family: 'Pretendard', 'Apple SD Gothic Neo', sans-serif;
    }
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.2rem;
        background: linear-gradient(90deg, #ff7b54, #ff5e7e);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .sub-title {
        text-align: center;
        color: #888;
        margin-bottom: 1.8rem;
        font-size: 0.95rem;
    }
    .rank-card {
        background: linear-gradient(135deg, #1f2937, #111827);
        border-radius: 22px;
        padding: 2.2rem 1.5rem;
        text-align: center;
        color: white;
        box-shadow: 0 10px 30px rgba(0,0,0,0.25);
        margin-bottom: 1.5rem;
    }
    .rank-number {
        font-size: 3.6rem;
        font-weight: 900;
        line-height: 1.1;
        margin: 0.3rem 0;
    }
    .rank-label {
        font-size: 1rem;
        opacity: 0.75;
    }
    .stat-grid {
        display: flex;
        justify-content: space-between;
        gap: 0.8rem;
        margin-top: 1.5rem;
    }
    .stat-box {
        flex: 1;
        background: #f8f9fb;
        border-radius: 16px;
        padding: 1rem 0.5rem;
        text-align: center;
        border: 1px solid #eee;
    }
    .stat-value {
        font-size: 1.3rem;
        font-weight: 800;
        color: #222;
    }
    .stat-label {
        font-size: 0.78rem;
        color: #999;
        margin-top: 0.2rem;
    }
    .badge {
        display: inline-block;
        padding: 0.3rem 0.9rem;
        border-radius: 999px;
        font-size: 0.85rem;
        font-weight: 700;
        margin-top: 0.6rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown('<div class="main-title">🌡️ 서울 역대 기온 랭킹</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">달력에서 기간을 선택하면, 같은 기간(월/일 기준) 역대 기록 중 몇 위인지 알려드려요</div>',
    unsafe_allow_html=True,
)


# ----------------------------------------------------
# 데이터 로드
# ----------------------------------------------------
@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = [c.strip() for c in df.columns]
    df["날짜"] = df["날짜"].astype(str).str.strip()
    df = df[df["날짜"] != ""]
    df["날짜"] = pd.to_datetime(df["날짜"], errors="coerce")
    df = df.dropna(subset=["날짜"])
    df["평균기온"] = pd.to_numeric(df["평균기온"], errors="coerce")
    df["최저기온"] = pd.to_numeric(df["최저기온"], errors="coerce")
    df["최고기온"] = pd.to_numeric(df["최고기온"], errors="coerce")
    df = df.sort_values("날짜").reset_index(drop=True)
    return df


try:
    df = load_data(CSV_PATH)
except FileNotFoundError:
    st.error(f"'{CSV_PATH}' 파일을 찾을 수 없습니다. app.py와 같은 폴더에 seoul.csv를 함께 업로드해주세요.")
    st.stop()

min_date = df["날짜"].min().date()
max_date = df["날짜"].max().date()

# ----------------------------------------------------
# 날짜 선택 (달력)
# ----------------------------------------------------
default_start = max_date - timedelta(days=6)
selected = st.date_input(
    "기간 선택",
    value=(default_start, max_date),
    min_value=min_date,
    max_value=max_date,
)

if not isinstance(selected, tuple) or len(selected) != 2:
    st.info("시작일과 종료일, 두 날짜를 선택해주세요.")
    st.stop()

start_date, end_date = selected
if start_date > end_date:
    start_date, end_date = end_date, start_date

period_days = (end_date - start_date).days + 1


# ----------------------------------------------------
# 같은 월/일 구간을 매년 기준으로 계산
# ----------------------------------------------------
def safe_date(year: int, month: int, day: int):
    """2/29처럼 존재하지 않는 날짜는 2/28로 보정"""
    try:
        return date(year, month, day)
    except ValueError:
        return date(year, month, 28)


@st.cache_data
def build_yearly_stats(_df: pd.DataFrame, s_month, s_day, e_month, e_day, days: int, min_year: int, max_year: int):
    records = []
    for y in range(min_year, max_year + 1):
        y_start = safe_date(y, s_month, s_day)
        y_end = y_start + timedelta(days=days - 1)
        mask = (_df["날짜"].dt.date >= y_start) & (_df["날짜"].dt.date <= y_end)
        window = _df.loc[mask]
        valid = window["평균기온"].dropna()
        # 최소 80% 이상 데이터가 있어야 유효한 연도로 인정
        if len(valid) >= max(1, int(days * 0.8)):
            records.append(
                {
                    "year": y,
                    "start": y_start,
                    "end": y_end,
                    "avg_temp": round(valid.mean(), 2),
                    "coverage": len(valid),
                }
            )
    return pd.DataFrame(records)


stats_df = build_yearly_stats(
    df, start_date.month, start_date.day, end_date.month, end_date.day,
    period_days, min_date.year, max_date.year,
)

if stats_df.empty:
    st.warning("해당 기간에 대한 유효한 역대 데이터가 부족합니다.")
    st.stop()

# 선택한 기간 자체의 값 (해당 연도 기록이 유효 목록에 없을 수도 있으니 직접 재계산)
mask_sel = (df["날짜"].dt.date >= start_date) & (df["날짜"].dt.date <= end_date)
sel_window = df.loc[mask_sel]
sel_valid = sel_window["평균기온"].dropna()

if len(sel_valid) == 0:
    st.warning("선택한 기간에는 관측된 기온 데이터가 없습니다.")
    st.stop()

sel_avg = round(sel_valid.mean(), 2)
sel_coverage = len(sel_valid)
sel_total = period_days

# stats_df에 선택 연도가 없으면(데이터 부족 등) 강제로 추가하여 랭킹에 포함
if start_date.year not in stats_df["year"].values:
    stats_df = pd.concat(
        [stats_df, pd.DataFrame([{
            "year": start_date.year, "start": start_date, "end": end_date,
            "avg_temp": sel_avg, "coverage": sel_coverage,
        }])],
        ignore_index=True,
    )
else:
    stats_df.loc[stats_df["year"] == start_date.year, "avg_temp"] = sel_avg

# ----------------------------------------------------
# 랭킹 계산
# ----------------------------------------------------
stats_df = stats_df.sort_values("avg_temp", ascending=False).reset_index(drop=True)
stats_df["hot_rank"] = stats_df["avg_temp"].rank(ascending=False, method="min").astype(int)
stats_df["cold_rank"] = stats_df["avg_temp"].rank(ascending=True, method="min").astype(int)

total_years = len(stats_df)
row = stats_df[stats_df["year"] == start_date.year].iloc[0]
hot_rank = int(row["hot_rank"])
cold_rank = int(row["cold_rank"])
percentile = round((1 - (hot_rank - 1) / total_years) * 100, 1)

hist_mean = round(stats_df["avg_temp"].mean(), 2)
hist_max = stats_df["avg_temp"].max()
hist_min = stats_df["avg_temp"].min()
diff_from_mean = round(sel_avg - hist_mean, 2)

# 뱃지 색상/문구
if hot_rank <= max(1, round(total_years * 0.05)):
    badge_text, badge_color = "🔥 역대급 더위", "#ff4d4f"
elif hot_rank <= max(1, round(total_years * 0.2)):
    badge_text, badge_color = "😎 상위권 더위", "#ff8c42"
elif cold_rank <= max(1, round(total_years * 0.05)):
    badge_text, badge_color = "🥶 역대급 추위", "#3b82f6"
elif cold_rank <= max(1, round(total_years * 0.2)):
    badge_text, badge_color = "❄️ 상위권 추위", "#60a5fa"
else:
    badge_text, badge_color = "🙂 평년 수준", "#9ca3af"

# ----------------------------------------------------
# 결과 카드
# ----------------------------------------------------
period_label = f"{start_date.strftime('%Y.%m.%d')} ~ {end_date.strftime('%Y.%m.%d')}  ({period_days}일간)"

st.markdown(
    f"""
    <div class="rank-card">
        <div class="rank-label">{period_label}</div>
        <div class="rank-number">역대 {hot_rank}위</div>
        <div class="rank-label">더운 기간 &nbsp;·&nbsp; 전체 {total_years}개 연도 중</div>
        <span class="badge" style="background:{badge_color};">{badge_text}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

c1, c2, c3, c4 = st.columns(4)
c1.markdown(f'<div class="stat-box"><div class="stat-value">{sel_avg}°C</div><div class="stat-label">기간 평균기온</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="stat-box"><div class="stat-value">{hist_mean}°C</div><div class="stat-label">역대 평균</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="stat-box"><div class="stat-value">{"+" if diff_from_mean>=0 else ""}{diff_from_mean}°C</div><div class="stat-label">평년 대비</div></div>', unsafe_allow_html=True)
c4.markdown(f'<div class="stat-box"><div class="stat-value">상위 {percentile}%</div><div class="stat-label">백분위</div></div>', unsafe_allow_html=True)

st.write("")
st.caption(f"추위 기준으로는 역대 {cold_rank}위 (추운 순위) · 데이터 커버리지 {sel_coverage}/{sel_total}일")

# ----------------------------------------------------
# 시각화: 연도별 평균기온 분포 + 선택 연도 하이라이트
# ----------------------------------------------------
st.subheader("📊 같은 기간, 연도별 평균기온 분포")

chart_df = stats_df.copy()
chart_df["highlight"] = chart_df["year"] == start_date.year
chart_df = chart_df.sort_values("year")

base = alt.Chart(chart_df).encode(
    x=alt.X("year:O", title="연도", axis=alt.Axis(labelAngle=-45, labelOverlap=True)),
    y=alt.Y("avg_temp:Q", title="평균기온 (°C)"),
    tooltip=[
        alt.Tooltip("year:O", title="연도"),
        alt.Tooltip("avg_temp:Q", title="평균기온", format=".2f"),
        alt.Tooltip("hot_rank:Q", title="더위 순위"),
    ],
)

bars = base.mark_bar(color="#d1d5db", cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
    color=alt.condition(
        alt.datum.highlight,
        alt.value("#ff5e7e"),
        alt.value("#d1d5db"),
    )
)

rule = alt.Chart(pd.DataFrame({"y": [hist_mean]})).mark_rule(
    color="#9ca3af", strokeDash=[4, 4]
).encode(y="y:Q")

chart = (bars + rule).properties(height=340).configure_view(strokeWidth=0)
st.altair_chart(chart, use_container_width=True)
st.caption("점선은 역대 평균, 분홍색 막대가 선택하신 기간에 해당하는 연도입니다.")

# ----------------------------------------------------
# 상위/하위 랭킹 테이블
# ----------------------------------------------------
with st.expander("🏆 역대 순위 TOP 10 (더운 순)"):
    top10 = stats_df.sort_values("hot_rank").head(10)[["hot_rank", "year", "avg_temp"]]
    top10.columns = ["순위", "연도", "평균기온(°C)"]
    st.dataframe(top10.set_index("순위"), use_container_width=True)

with st.expander("🥶 역대 순위 TOP 10 (추운 순)"):
    bottom10 = stats_df.sort_values("cold_rank").head(10)[["cold_rank", "year", "avg_temp"]]
    bottom10.columns = ["순위", "연도", "평균기온(°C)"]
    st.dataframe(bottom10.set_index("순위"), use_container_width=True)

st.markdown("---")
st.caption(f"데이터 기간: {min_date} ~ {max_date} · 출처: seoul.csv (기상청 서울 관측소)")
