from pathlib import Path
import html
import math

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# =========================================================
# 0. 페이지 기본 설정
# =========================================================

st.set_page_config(
    page_title="서울 공영주차장 탐색 대시보드",
    page_icon="🅿️",
    layout="wide"
)

HERE = Path(__file__).parent
DATA_PATH = HERE / "parking.csv"

NAVY = "#203B60"
BLUE = "#2874B8"
TEAL = "#169B80"
ORANGE = "#D17C24"
GRAY = "#8A96A8"

FEE_ORDER = [
    "유료",
    "무료",
    "혼합",
    "기타·미상"
]

FEE_COLORS = {
    "유료": "#2874B8",
    "무료": "#169B80",
    "혼합": "#E5A231",
    "기타·미상": "#8A96A8"
}


# =========================================================
# 1. CSS
# =========================================================

st.markdown(
    """
    <style>

    .block-container {
        max-width: 1420px;
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }

    [data-testid="stMetric"] {
        border: 1px solid #dbe4ed;
        border-radius: 16px;
        padding: 16px 18px;
        background: white;
    }

    .hero {
        background: linear-gradient(
            115deg,
            #142942,
            #244e70
        );

        border-radius: 22px;
        padding: 30px 34px;
        margin-bottom: 16px;
    }

    .hero .eyebrow {
        color: #8de0d1;
        font-size: 12px;
        letter-spacing: 2.5px;
        font-weight: 700;
    }

    .hero h1 {
        color: white;
        font-size: 32px;
        line-height: 1.35;
        margin: 8px 0 10px 0;
    }

    .hero p {
        color: #d8e4f0;
        font-size: 15px;
        line-height: 1.7;
        margin: 0;
    }

    .insight {
        border-left: 4px solid #169B80;
        padding: 12px 16px;
        border-radius: 0 10px 10px 0;
        background: #edf8f5;
        color: #183e37;
        margin: 8px 0;
        line-height: 1.75;
    }

    .note {
        border-left: 4px solid #2874B8;
        padding: 12px 16px;
        border-radius: 0 10px 10px 0;
        background: #eef5fb;
        color: #203B60;
        margin: 8px 0;
        line-height: 1.75;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# =========================================================
# 2. 상단 제목
# =========================================================

st.markdown(
    """<div class="hero">
<div class="eyebrow">SEOUL PARKING / PUBLIC DATA EXPLORER</div>
<h1>서울 공영주차장, 자치구별 탐색<br>규모·요금 유형·위치를 한눈에</h1>
<p>자치구별 주차면수를 비교하고, 선택한 지역의 주차장 규모와 요금 유형을 살펴보세요.
원하는 조건의 주차장은 지도와 목록에서 확인할 수 있습니다.</p>
</div>""",
    unsafe_allow_html=True
)

st.caption(
    "출처: 공공데이터포털 · 전국주차장정보표준데이터 | "
    "원자료의 등록 기록 기준이며, "
    "실시간 빈자리 정보는 제공하지 않습니다."
)

# =========================================================
# 3. 함수
# =========================================================

@st.cache_data
def read_data(path_string, modified_time):

    return pd.read_csv(
        path_string,
        encoding="cp949",
        low_memory=False
    )


def clean_number(series):

    return pd.to_numeric(
        series
        .astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("원", "", regex=False)
        .str.replace("분", "", regex=False)
        .str.strip(),
        errors="coerce"
    )


def fmt_num(value, suffix=""):

    if pd.isna(value):
        return "정보 없음"

    value = float(value)

    if value.is_integer():
        return f"{value:,.0f}{suffix}"

    return f"{value:,.1f}{suffix}"


def insight(text):

    st.markdown(
        '<div class="insight">'
        + html.escape(text)
        + "</div>",
        unsafe_allow_html=True
    )


def note(text):

    st.markdown(
        '<div class="note">'
        + html.escape(text)
        + "</div>",
        unsafe_allow_html=True
    )


def style(fig, height=410):

    fig.update_layout(
        template="plotly_white",
        height=height,
        font=dict(
            family="Arial, sans-serif",
            size=13,
            color=NAVY
        ),
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(
            l=20,
            r=30,
            t=45,
            b=30
        ),
        hoverlabel=dict(
            font_size=13
        )
    )

    fig.update_xaxes(
        showgrid=False,
        zeroline=False,
        automargin=True
    )

    fig.update_yaxes(
        gridcolor="#E8EDF2",
        zeroline=False,
        automargin=True
    )

    return fig


def show(fig, key):

    st.plotly_chart(
        fig,
        width="stretch",
        theme=None,
        key=key,
        config={
            "displaylogo": False
        }
    )

def show_map(fig, key):
    st.plotly_chart(
        fig,
        width="stretch",
        theme=None,
        key=key,
        config={
            "displaylogo": False,
            "scrollZoom": False
        }
    )


def detect_col(df, candidates):

    for col in candidates:

        if col in df.columns:
            return col

    return None


# =========================================================
# 4. 데이터 불러오기
# =========================================================

if not DATA_PATH.exists():

    st.error(
        "app.py와 같은 폴더에 parking.csv를 넣어 주세요."
    )

    st.stop()


data = read_data(
    str(DATA_PATH),
    DATA_PATH.stat().st_mtime_ns
)


required = [
    "소재지도로명주소",
    "소재지지번주소",
    "주차장구분",
    "주차장명",
    "주차구획수",
    "요금정보",
    "위도",
    "경도"
]


missing = [
    col
    for col in required
    if col not in data.columns
]


if missing:

    st.error(
        "필수 열이 없습니다: "
        + ", ".join(missing)
    )

    st.stop()


# =========================================================
# 5. 서울 공영주차장만 추출
# =========================================================

road = (
    data["소재지도로명주소"]
    .fillna("")
    .astype(str)
    .str.strip()
)

lot = (
    data["소재지지번주소"]
    .fillna("")
    .astype(str)
    .str.strip()
)


is_seoul = (
    road.str.startswith("서울특별시")
    |
    lot.str.startswith("서울특별시")
)


is_public = (
    data["주차장구분"]
    .fillna("")
    .astype(str)
    .str.strip()
    .eq("공영")
)


seoul = data.loc[
    is_seoul & is_public
].copy()


# =========================================================
# 6. 자치구 / 주소
# =========================================================

road_gu = road.str.extract(
    r"^서울특별시\s+(\S+구)",
    expand=False
)

lot_gu = lot.str.extract(
    r"^서울특별시\s+(\S+구)",
    expand=False
)


seoul["자치구"] = (
    road_gu
    .fillna(lot_gu)
    .loc[seoul.index]
)


seoul["주소"] = (
    road
    .where(
        road.ne(""),
        lot
    )
    .loc[seoul.index]
)


seoul["주차장명"] = (
    seoul["주차장명"]
    .fillna("이름 미상")
    .astype(str)
    .str.strip()
)


# =========================================================
# 7. 규모 정제
# =========================================================

seoul["규모_면"] = clean_number(
    seoul["주차구획수"]
)

seoul.loc[
    seoul["규모_면"] < 0,
    "규모_면"
] = np.nan


# =========================================================
# 8. 요금 유형
# =========================================================

fee_raw = (
    seoul["요금정보"]
    .fillna("")
    .astype(str)
    .str.strip()
)


seoul["요금유형"] = fee_raw.where(
    fee_raw.isin(
        FEE_ORDER[:3]
    ),
    "기타·미상"
)


# =========================================================
# 9. 좌표
# =========================================================

for col in [
    "위도",
    "경도"
]:

    seoul[col] = pd.to_numeric(
        seoul[col],
        errors="coerce"
    )


# 원자료 위치 확인용
seoul["원자료행"] = (
    seoul.index + 2
)

seoul["행ID"] = seoul["원자료행"].astype(str)

# =========================================================
# 10. 요금 상세 열 자동 탐색
# =========================================================

base_time_col = detect_col(
    seoul,
    [
        "기본주차시간",
        "기본시간"
    ]
)


base_fee_col = detect_col(
    seoul,
    [
        "기본주차요금",
        "기본요금"
    ]
)


add_time_col = detect_col(
    seoul,
    [
        "추가단위시간",
        "추가시간"
    ]
)


add_fee_col = detect_col(
    seoul,
    [
        "추가단위요금",
        "추가요금"
    ]
)


HAS_FEE_DETAIL = all(
    [
        base_time_col,
        base_fee_col,
        add_time_col,
        add_fee_col
    ]
)


# =========================================================
# 11. 1시간 예상 요금 계산
# =========================================================

if HAS_FEE_DETAIL:

    seoul["_기본시간"] = clean_number(
        seoul[base_time_col]
    )

    seoul["_기본요금"] = clean_number(
        seoul[base_fee_col]
    )

    seoul["_추가시간"] = clean_number(
        seoul[add_time_col]
    )

    seoul["_추가요금"] = clean_number(
        seoul[add_fee_col]
    )


    def estimate_fee_60(row):

        # 무료로 분류된 기록은 0원으로 처리
        if row["요금유형"] == "무료":
            return 0.0

        # 요금 유형을 모르면 계산하지 않음
        if row["요금유형"] not in ["유료", "혼합"]:
            return np.nan

        bt = row["_기본시간"]
        bf = row["_기본요금"]
        at = row["_추가시간"]
        af = row["_추가요금"]

        # 기본시간과 기본요금이 유효한지 확인
        if not np.isfinite(bt) or not np.isfinite(bf):
            return np.nan

        if bt <= 0 or bf < 0:
            return np.nan

        # 60분이 기본시간 안에 포함되는 경우
        if bt >= 60:
            return float(bf)

        # 추가시간과 추가요금이 유효한지 확인
        if not np.isfinite(at) or not np.isfinite(af):
            return np.nan

        if at <= 0 or af < 0:
            return np.nan

        extra_units = math.ceil((60 - bt) / at)

        total = bf + extra_units * af

        return float(total)


    seoul["1시간예상요금"] = seoul.apply(
        estimate_fee_60,
        axis=1
    )


# =========================================================
# 12. 자치구 목록
# =========================================================

districts = sorted(
    seoul["자치구"]
    .dropna()
    .unique()
)


if not districts:

    st.warning(
        "서울 공영주차장의 자치구 정보를 찾지 못했습니다."
    )

    st.stop()


# =========================================================
# 13. 자치구 단위 요약
# =========================================================

district_summary = (
    seoul
    .dropna(
        subset=["자치구"]
    )
    .groupby(
        "자치구"
    )
    .agg(

        데이터건수=(
            "주차장명",
            "size"
        ),

        총주차면=(
            "규모_면",
            "sum"
        ),

        중앙주차면=(
            "규모_면",
            "median"
        ),

        평균주차면=(
            "규모_면",
            "mean"
        ),

        무료건수=(
            "요금유형",
            lambda x:
            (x == "무료").sum()
        ),

        유료건수=(
            "요금유형",
            lambda x:
            (x == "유료").sum()
        )

    )
    .reset_index()
)


district_summary["무료비율"] = (
    district_summary["무료건수"]
    /
    district_summary["데이터건수"]
    *
    100
)


# =========================================================
# 14. 서울 평균
# =========================================================

city_mean_count = (
    district_summary[
        "데이터건수"
    ].mean()
)


city_mean_total_spaces = (
    district_summary[
        "총주차면"
    ].mean()
)


city_mean_median_spaces = (
    district_summary[
        "중앙주차면"
    ].mean()
)


city_mean_free_rate = (
    district_summary[
        "무료비율"
    ].mean()
)


# 자치구 평균 대비 배율
district_summary[
    "건수_서울평균배율"
] = (
    district_summary["데이터건수"]
    /
    city_mean_count
)


district_summary[
    "총면수_서울평균배율"
] = (
    district_summary["총주차면"]
    /
    city_mean_total_spaces
)


district_summary[
    "중앙규모_서울평균배율"
] = (
    district_summary["중앙주차면"]
    /
    city_mean_median_spaces
)


if city_mean_free_rate > 0:

    district_summary[
        "무료비율_서울평균배율"
    ] = (
        district_summary["무료비율"]
        /
        city_mean_free_rate
    )

else:

    district_summary[
        "무료비율_서울평균배율"
    ] = np.nan


# =========================================================
# 15. 사이드바
# =========================================================

with st.sidebar:

    st.markdown(
        "### 🅿️ 서울 주차 데이터"
    )


    default_index = (
        districts.index("동대문구")
        if "동대문구" in districts
        else 0
    )


    selected_district = st.selectbox(
        "자치구 선택",
        districts,
        index=default_index
    )


    st.divider()


    available_fee_types = [
    fee_type
    for fee_type in FEE_ORDER
    if (seoul["요금유형"] == fee_type).any()
    ]
    
    selected_fee_types = st.multiselect(
    "요금 유형",
    available_fee_types,
    default=available_fee_types
    )


    valid_all_sizes = (
        seoul["규모_면"]
        .dropna()
    )


    if valid_all_sizes.empty:

        max_size = 0

    else:

        max_size = int(
            valid_all_sizes.max()
        )


    min_spaces = st.number_input(
        "최소 주차구획수",
        min_value=0,
        max_value=max(
            0,
            max_size
        ),
        value=0,
        step=10
    )


    st.divider()


    st.caption(
        "요금 유형·최소 주차구획수 필터는 "
        "'주차장 찾기' 탭 전체와 "
        "'데이터·한계' 탭의 목록·CSV 다운로드에 적용됩니다. "
        "상단 요약 지표와 '선택 지역 분석'은 선택한 자치구 전체, "
        "'서울 전체 비교'는 서울 전체 데이터를 기준으로 합니다."
    )


# =========================================================
# 16. 선택 자치구
# =========================================================

view = seoul.loc[
    seoul["자치구"]
    ==
    selected_district
].copy()


filtered_view = view.loc[
    view["요금유형"]
    .isin(
        selected_fee_types
    )
    &
    (
        view["규모_면"]
        .fillna(-1)
        >=
        min_spaces
    )
].copy()


summary_row = (
    district_summary.loc[
        district_summary["자치구"]
        ==
        selected_district
    ]
    .iloc[0]
)


# =========================================================
# 17. 핵심 KPI
# =========================================================

st.subheader(
    f"{selected_district} 한눈에 보기"
)


c1, c2, c3, c4 = st.columns(4)


c1.metric(
    "등록 주차장 데이터",
    f"{int(summary_row['데이터건수']):,}건"
)

c1.caption(
    f"자치구 평균의 "
    f"{summary_row['건수_서울평균배율']:.2f}배"
)


c2.metric(
    "주차구획수 합계",
    fmt_num(summary_row["총주차면"], "면")
)

c2.caption(
    f"자치구 평균의 "
    f"{summary_row['총면수_서울평균배율']:.2f}배"
)


c3.metric(
    "주차장 규모 중앙값",
    fmt_num(summary_row["중앙주차면"], "면")
)

c3.caption(
    f"자치구별 중앙값 평균의 "
    f"{summary_row['중앙규모_서울평균배율']:.2f}배"
)


c4.metric(
    "무료 데이터 비율",
    f"{summary_row['무료비율']:.1f}%"
)

c4.caption(
    f"자치구별 무료 비율 평균: "
    f"{city_mean_free_rate:.1f}%"
)



note(
    "단순 주차장 건수만으로 지역의 주차 환경을 판단하지 않고, "
    "등록 건수·총 주차면수·전형적인 주차장 규모·무료 비율을 함께 비교합니다."
)


# =========================================================
# 18. 탭
# =========================================================

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "🗺️ 주차장 찾기",
        "📊 서울 전체 비교",
        "🔎 선택 지역 분석",
        "📋 데이터·한계"
    ]
)


# =========================================================
# TAB 1
# 주차장 찾기
# =========================================================

with tab1:

    st.markdown(
        f"### {selected_district} 공영주차장 탐색"
    )

    st.caption(
        "원하는 조건의 주차장을 지도에서 확인하고 "
        "규모가 큰 시설을 비교할 수 있습니다."
    )


    valid_coords = (
        filtered_view["위도"]
        .between(-90, 90)
        &
        filtered_view["경도"]
        .between(-180, 180)
        &
        filtered_view["위도"]
        .ne(0)
        &
        filtered_view["경도"]
        .ne(0)
    )


    map_data = filtered_view.loc[
        valid_coords
    ].copy()


    if map_data.empty:

        st.info(
            "현재 필터 조건에서 지도에 표시할 수 있는 "
            "주차장이 없습니다."
        )

    else:

        map_fig = px.scatter_map(

            map_data,

            lat="위도",

            lon="경도",

            color="요금유형",

            hover_name="주차장명",

            hover_data={
                "규모_면": True,
                "주소": True,
                "원자료행": True,
                "위도": False,
                "경도": False
            },

            labels={
                "규모_면":
                "주차구획수 (면)"
            },

            category_orders={
                "요금유형":
                FEE_ORDER
            },

            color_discrete_map=
            FEE_COLORS,

            map_style=
            "carto-positron",

            zoom=12,

            center={
                "lat":
                map_data["위도"].mean(),

                "lon":
                map_data["경도"].mean()
            }
        )


        map_fig.update_traces(

            marker=dict(
                size=13,
                opacity=.85
            )

        )


        style(
            map_fig,
            570
        )


        map_fig.update_layout(

            dragmode="pan",

            margin=dict(
                l=0,
                r=0,
                t=10,
                b=0
            ),

            legend=dict(
                orientation="h",
                y=1.05,
                title=""
            )

        )


        show_map(
            map_fig,
            f"map_{selected_district}_{min_spaces}"
)


        st.caption(
            f"현재 필터 기준 "
            f"{len(map_data):,}건 표시 · "
            "점 위에 마우스를 올리면 "
            "주차장명·규모·주소를 볼 수 있습니다."
        )


    # -------------------------------------------------
    # 규모 TOP 10
    # -------------------------------------------------

    st.markdown(
        "#### 규모가 큰 주차장 TOP 10"
    )


    top10_map = (

        filtered_view

        .dropna(
            subset=["규모_면"]
        )

        .nlargest(
            10,
            "규모_면"
        )

        .copy()
    )


    if top10_map.empty:

        st.info(
            "현재 조건에서 주차구획수 정보가 있는 "
            "주차장이 없습니다."
        )

    else:

        top10_plot = top10_map.sort_values(
            "규모_면"
        )


        fig_top = px.bar(

            top10_plot,

            x="규모_면",

            y="행ID",

            orientation="h",

            color="요금유형",

            color_discrete_map=
            FEE_COLORS,

            custom_data=[
                "주소",
                "원자료행",
                "주차장명"
            ],

            labels={
                "규모_면":
                "주차구획수 (면)",

                "행ID": ""
            }

        )


        style(
            fig_top,
            470
        )


        fig_top.update_traces(

            texttemplate=
            "%{x:,.0f}면",

            textposition=
            "outside",

            cliponaxis=
            False,

            hovertemplate=(
                "%{customdata[2]}<br>"
                "%{x:,.0f}면<br>"
                "%{customdata[0]}<br>"
                "원자료 %{customdata[1]}행"
                "<extra></extra>"
            )

        )


        fig_top.update_xaxes(

            range=[
                0,
                top10_plot[
                    "규모_면"
                ].max()
                *
                1.28
            ],

            showgrid=True,

            gridcolor=
            "#E8EDF2"

        )

        fig_top.update_yaxes(
            type="category",
            categoryorder="array",
            categoryarray=top10_plot["행ID"].tolist(),
            tickmode="array",
            tickvals=top10_plot["행ID"].tolist(),
            ticktext=top10_plot["주차장명"].tolist(),
            title_text=""
        )


        show(
            fig_top,
            "top10_parking"
        )


        biggest = top10_map.iloc[0]


        insight(
            f"{selected_district}에서 현재 조건 기준 "
            f"가장 큰 주차장 기록은 "
            f"{biggest['주차장명']}이며 "
            f"{fmt_num(biggest['규모_면'], '면')}입니다."
        )


# =========================================================
# TAB 2
# 서울 전체 비교
# =========================================================

with tab2:

    st.markdown(
        "### 서울 25개 자치구, 어디가 어떻게 다른가?"
    )


    st.caption(
        "단순한 주차장 개수뿐 아니라 "
        "총 주차면수·주차장 규모·무료 비율을 함께 비교합니다."
    )


    metric_name = st.selectbox(

        "비교할 지표",

        [
            "총 주차면수",
            "등록 데이터 건수",
            "주차장 규모 중앙값",
            "무료 데이터 비율"
        ]

    )


    metric_map = {

        "총 주차면수":
        (
            "총주차면",
            "면"
        ),

        "등록 데이터 건수":
        (
            "데이터건수",
            "건"
        ),

        "주차장 규모 중앙값":
        (
            "중앙주차면",
            "면"
        ),

        "무료 데이터 비율":
        (
            "무료비율",
            "%"
        )

    }


    metric_col, metric_unit = (
        metric_map[
            metric_name
        ]
    )


    ranked = (
        district_summary

        .sort_values(
            metric_col,
            ascending=True
        )

        .copy()
    )


    fig_rank = px.bar(

        ranked,

        x=metric_col,

        y="자치구",

        orientation="h",

        labels={

            metric_col:
            f"{metric_name} ({metric_unit})",

            "자치구":
            ""

        }

    )


    style(
        fig_rank,
        700
    )


    bar_colors = [

        TEAL
        if gu == selected_district
        else NAVY

        for gu
        in ranked["자치구"]

    ]


    if metric_unit == "%":

        text_template = "%{x:.1f}%"

        hover_template = (
            "%{y}<br>"
            "%{x:.1f}%"
            "<extra></extra>"
        )

    else:

        text_template = "%{x:,.0f}"

        hover_template = (
            "%{y}<br>"
            "%{x:,.0f}"
            + metric_unit
            + "<extra></extra>"
        )


    fig_rank.update_traces(

        marker_color=
        bar_colors,

        texttemplate=
        text_template,

        textposition=
        "outside",

        cliponaxis=
        False,

        hovertemplate=
        hover_template

    )


    if metric_col == "총주차면":

        mean_value = (
            city_mean_total_spaces
        )

    elif metric_col == "데이터건수":

        mean_value = (
            city_mean_count
        )

    elif metric_col == "중앙주차면":

        mean_value = (
            city_mean_median_spaces
        )

    else:

        mean_value = (
            city_mean_free_rate
        )


    fig_rank.add_vline(

        x=mean_value,

        line_dash=
        "dash",

        line_color=
        ORANGE,

        annotation_text=
        "서울 자치구 평균",

        annotation_position=
        "top"

    )


    max_value = ranked[
        metric_col
    ].max()


    fig_rank.update_xaxes(

        range=[
            0,
            max(
                max_value * 1.18,
                mean_value * 1.18
            )
        ],

        showgrid=True,

        gridcolor=
        "#E8EDF2"

    )

    st.caption(
    "주황색 점선은 서울 25개 자치구의 평균값입니다. "
    "막대가 점선 오른쪽이면 평균보다 높고, 왼쪽이면 평균보다 낮습니다."
)

    show(
        fig_rank,
        f"rank_{metric_col}"
    )

# =========================================================
# TAB 3
# 선택 지역 심층 분석
# =========================================================

with tab3:

    st.markdown(
        f"### {selected_district}의 내부 구성"
    )


    left, right = st.columns(
        [
            1.05,
            1
        ]
    )


    # -------------------------------------------------
    # 요금 구성
    # -------------------------------------------------

    with left:

        st.markdown(
            "#### 요금 유형 구성"
        )


        fee_counts = (

            view["요금유형"]

            .value_counts()

            .reindex(
                FEE_ORDER,
                fill_value=0
            )

            .rename_axis(
                "요금유형"
            )

            .reset_index(
                name="건수"
            )

        )


        fee_counts = fee_counts.loc[
            fee_counts["건수"]
            >
            0
        ]


        donut = px.pie(

            fee_counts,

            names=
            "요금유형",

            values=
            "건수",

            color=
            "요금유형",

            hole=
            .68,

            color_discrete_map=
            FEE_COLORS,

            category_orders={
                "요금유형":
                FEE_ORDER
            }

        )


        style(
            donut,
            380
        )


        donut.update_traces(

            textposition=
            "outside",

            textinfo=
            "label+percent",

            sort=
            False,

            marker=dict(

                line=dict(
                    color="white",
                    width=3
                )

            )

        )


        donut.update_layout(

            showlegend=
            False,

            annotations=[

                dict(

                    text=(
                        f"<b>{len(view):,}</b>"
                        "<br>등록 건수"
                    ),

                    x=
                    .5,

                    y=
                    .5,

                    showarrow=
                    False,

                    font=dict(
                        size=18,
                        color=NAVY
                    )

                )

            ]

        )


        show(
            donut,
            "district_fee_donut"
        )


        most_fee = (
            fee_counts

            .sort_values(
                "건수",
                ascending=False
            )

            .iloc[0]
        )


        insight(
            f"{selected_district}에서는 "
            f"{most_fee['요금유형']} 유형이 가장 많으며 "
            f"{int(most_fee['건수']):,}건입니다."
        )


    # -------------------------------------------------
    # 규모 분포
    # -------------------------------------------------

    with right:

        st.markdown(
            "#### 주차장 규모 분포"
        )


        sizes = (
            view["규모_면"]
            .dropna()
        )


        if sizes.empty:

            st.info(
                "유효한 주차구획수 정보가 없습니다."
            )

        else:

            q1 = (
                sizes.quantile(
                    .25
                )
            )

            median = (
                sizes.median()
            )

            q3 = (
                sizes.quantile(
                    .75
                )
            )


            box = go.Figure()


            box.add_trace(

                go.Box(

                    x=
                    sizes,

                    name=
                    selected_district,

                    orientation=
                    "h",

                    boxmean=
                    True,

                    marker_color=
                    TEAL,

                    line_color=
                    NAVY,

                    hovertemplate=
                    "%{x:,.0f}면"
                    "<extra></extra>"

                )

            )


            style(
                box,
                270
            )


            box.update_xaxes(

                title=
                "주차구획수 (면)",

                showgrid=
                True,

                gridcolor=
                "#E8EDF2"

            )


            box.update_yaxes(
                showticklabels=False
            )


            # 겹쳐 나오는 기본 설명창 끄기
            box.update_traces(
                hovertemplate=None,
                hoverinfo="skip"
            )

            show(
                box,
                "district_box"
            )

            # 주요 통계값을 그래프 아래에 표시
            st.markdown(
                f"**최솟값:** {fmt_num(sizes.min(), '면')} · "
                f"**중앙값:** {fmt_num(median, '면')} · "
                f"**평균:** {fmt_num(sizes.mean(), '면')} · "
                f"**최댓값:** {fmt_num(sizes.max(), '면')}"
            )


            st.caption(
                "상자는 전체 데이터의 중간 50% 구간을 나타냅니다. "
                "상자 안의 실선은 중앙값, 점선은 평균입니다. "
                "수염 밖의 점은 이상치 판정 기준을 벗어난 값이며, "
                "반드시 데이터 오류를 뜻하지는 않습니다."
            )


            insight(
                f"중앙값은 "
                f"{fmt_num(median, '면')}이며, "
                f"중간 50%의 주차장은 약 "
                f"{fmt_num(q1, '면')}~"
                f"{fmt_num(q3, '면')} 범위입니다."
            )


    # -------------------------------------------------
    # 서울 평균과 비교
    # -------------------------------------------------

    st.markdown(
        "#### 서울 자치구 평균과 비교"
    )


    ratio_plot = pd.DataFrame(

        {

            "지표": [
                "등록 건수",
                "총 주차면수",
                "규모 중앙값",
                "무료 비율"
            ],

            "자치구 평균 대비 배율": [

                summary_row[
                    "건수_서울평균배율"
                ],

                summary_row[
                    "총면수_서울평균배율"
                ],

                summary_row[
                    "중앙규모_서울평균배율"
                ],

                summary_row[
                    "무료비율_서울평균배율"
                ]

            ]

        }

    )


    fig_compare = px.bar(

        ratio_plot,

        x=
        "지표",

        y=
        "자치구 평균 대비 배율",

        text=
        "자치구 평균 대비 배율"

    )


    style(
        fig_compare,
        410
    )


    fig_compare.update_traces(

        marker_color=[

            TEAL
            if value >= 1
            else BLUE

            for value
            in ratio_plot[
                "자치구 평균 대비 배율"
            ]

        ],

        texttemplate=
        "%{text:.2f}배",

        textposition=
        "outside"

    )


    fig_compare.add_hline(

        y=
        1,

        line_dash=
        "dash",

        line_color=
        ORANGE,

        annotation_text=
        "자치구 평균 = 1.00"

    )


    max_ratio = (
        ratio_plot[
            "자치구 평균 대비 배율"
        ]
        .dropna()
        .max()
    )


    if pd.isna(max_ratio):

        max_ratio = 1


    fig_compare.update_yaxes(

        title=
        "자치구 평균 대비 배율",

        range=[
            0,
            max(
                1.35,
                max_ratio * 1.2
            )
        ]

    )


    show(
        fig_compare,
        "district_vs_seoul"
    )


# =========================================================
# TAB 4
# 데이터 및 해석 한계
# =========================================================

with tab4:

    st.markdown(
        "### 선택한 자치구의 주차장 목록"
    )


    display_cols = [

        "주차장명",

        "자치구",

        "주차구획수",

        "요금정보",

        "주소",

        "원자료행"

    ]


    st.dataframe(

        filtered_view[
            display_cols
        ],

        hide_index=
        True,

        width=
        "stretch"

    )


    st.download_button(

        "현재 필터 결과 CSV 다운로드",

        filtered_view
        .to_csv(
            index=False
        )
        .encode(
            "utf-8-sig"
        ),

        file_name=(
            f"seoul_parking_"
            f"{selected_district}.csv"
        ),

        mime=
        "text/csv"

    )


    st.divider()


    st.markdown("### 데이터 출처와 해석 안내")

    st.markdown(
        "출처: "
        "[공공데이터포털 — 전국주차장정보표준데이터]"
        "(https://www.data.go.kr/data/15012896/standard.do)"
    )

    st.write(
        "**분석 대상** · 원자료에서 도로명주소 또는 지번주소가 "
        "'서울특별시'로 시작하고, 주차장구분이 '공영'인 데이터입니다. "
        "자치구별 비교에는 주소에서 자치구를 확인할 수 있는 데이터를 사용했습니다."
    )

    st.write(
        "**집계 기준과 중복** · 등록 건수는 원자료의 행 수이며, "
        "주차구획수 합계는 각 기록의 주차 칸 수를 더한 값입니다. "
        "관리번호가 반복된다는 이유만으로 기록을 삭제하지 않았습니다. "
        "동일 시설이 중복 등록돼 있다면 건수와 합계가 실제보다 커질 수 있으므로, "
        "등록 건수를 서로 다른 주차장의 수로 단정할 수 없습니다."
    )

    st.write(
        "**주차장 규모** · 규모는 주차구획수(면)를 뜻하며, "
        "중앙값은 규모를 작은 순서대로 나열했을 때 가운데에 해당하는 값입니다. "
        "숫자로 변환할 수 없거나 음수인 규모 값은 결측치로 처리했습니다."
    )

    st.write(
        "**요금 유형** · 제공기관이 등록한 유료·무료·혼합 값을 그대로 사용하고, "
        "그 외 값이나 빈 값은 '기타·미상'으로 표시했습니다. "
        "무료 비율은 해당 자치구의 전체 등록 건수 중 "
        "'무료'로 등록된 건수의 비율이며, 혼합은 포함하지 않습니다. "
        "최초 무료시간, 요일별 운영, 이용 대상별 감면 등은 "
        "이 구분만으로 알 수 없으므로 실제 이용 조건은 운영기관 안내를 확인해야 합니다."
    )

    st.write(
        "**자치구 평균과 배율** · 각 자치구의 지표 값을 같은 비중으로 평균 내고, "
        "선택한 구의 값을 그 평균으로 나누어 배율을 계산했습니다. "
        "1배는 평균과 같고, 0.5배는 평균의 절반, 2배는 평균의 두 배입니다. "
        "규모 중앙값의 비교 기준은 자치구별 중앙값의 평균이며, "
        "무료 비율의 비교 기준은 자치구별 무료 비율의 평균입니다. "
        "각각 서울 전체 기록을 한꺼번에 계산한 중앙값·무료 비율과는 다를 수 있습니다."
    )

    st.write(
        "**규모별 비율 히트맵** · 주차장 크기를 비교하기 위해 "
        "50면 미만, 50~99면, 100~199면, 200면 이상으로 구간을 나눴습니다. "
        "각 구의 규모 정보가 유효한 등록 데이터 건수를 기준으로 비율을 계산했으며, "
        "한 행의 합계는 약 100%입니다. "
        "이는 주차장 데이터의 건수 비율이며, 주차 칸 수의 비율은 아닙니다. "
        "유효한 규모 데이터가 없는 구는 빈칸으로 표시합니다."
    )

    st.write(
        "**박스플롯** · 상자는 제1사분위수(Q1)부터 제3사분위수(Q3)까지의 "
        "중간 50% 구간을 나타냅니다. "
        "상자 안의 실선은 중앙값, 점선은 평균입니다. "
        "수염은 Q1−1.5×IQR부터 Q3+1.5×IQR 사이에 있는 관측값까지 뻗으며, "
        "IQR은 Q3−Q1입니다. "
        "수염 밖의 점은 이 기준을 벗어난 값으로, 반드시 데이터 오류를 뜻하지는 않습니다."
    )



    st.write(
        "**지도** · 필터 결과 중 위도·경도가 숫자로 확인되고, "
        "좌표 범위 검사와 0 좌표 제외 조건을 통과한 기록만 표시합니다. "
        "좌표가 같은 기록은 점이 겹칠 수 있으며, "
        "범위 검사를 통과해도 실제 위치가 정확하다는 뜻은 아닙니다. "
        "실시간 빈자리 정보는 제공하지 않습니다."
    )

    st.write(
        "**데이터 기준일** · 각 기록의 정보가 어느 날짜를 기준으로 작성됐는지를 뜻합니다. "
        "아래 날짜 범위는 선택한 구의 기록 중 가장 이른 기준일과 가장 늦은 기준일입니다. "
        "분석 기간이나 파일 다운로드 날짜를 의미하지 않습니다."
    )

    st.write(
        "**해석의 한계** · 지역별 자료 누락과 갱신 시점 차이로 인해 "
        "등록 데이터가 실제 전체 공영주차장 현황을 완전히 나타내지 않을 수 있습니다. "
        "특히 등록 건수가 적은 구는 일부 기록만으로 비율이 크게 달라질 수 있습니다. "
        "인구·차량 수·주차 수요·시간대별 혼잡도를 반영하지 않았으므로, "
        "건수나 주차면수가 많다는 이유만으로 주차 환경이 더 좋거나 "
        "주차 공간이 충분하다고 판단할 수 없습니다."
    )

    if "데이터기준일자" in view.columns:

        dates = pd.to_datetime(
            view["데이터기준일자"],
            errors="coerce"
        ).dropna()

        if not dates.empty:

            st.caption(
                "선택한 구의 데이터 기준일 범위: "
                f"{dates.min():%Y-%m-%d}"
                " ~ "
                f"{dates.max():%Y-%m-%d}"
            )

    st.caption(
        "AI 활용: 코드 작성·시각화 설계·해석 문장 정리에 "
        "AI를 활용했습니다. 수치는 공개 CSV를 집계한 결과입니다."
    )


    # -------------------------------------------------
    # 데이터 점검
    # -------------------------------------------------

    with st.expander(
        "데이터 점검 내용 보기"
    ):

        st.write(
            "전국 주차장 데이터 건수:",
            len(data)
        )


        st.write(
            "서울 공영주차장 데이터 건수:",
            len(seoul)
        )


        st.write(
            "자치구 수:",
            len(districts)
        )


        st.write(
            "자치구 추출 불가 행 수:",
            int(
                seoul[
                    "자치구"
                ]
                .isna()
                .sum()
            )
        )

        st.write("서울 공영주차장 데이터 미리보기 — 처음 10행")

        st.dataframe(

            seoul.head(10),

            hide_index=
            True,

            width=
            "stretch"

        )


        if "주차장관리번호" in seoul.columns:

            ids = (

                seoul[
                    "주차장관리번호"
                ]

                .fillna("")

                .astype(str)

                .str.strip()

            )


            duplicate_mask = (

                ids.ne("")

                &

                ids.duplicated(
                    keep=False
                )

            )


            duplicates = seoul.loc[
                duplicate_mask
            ]


            st.write(
                "관리번호가 반복되는 행 수:",
                len(duplicates)
            )


            st.caption(
                "관리번호 반복이 반드시 동일 시설의 중복을 의미하지는 않습니다."
            )


            cols = [

                col

                for col in [

                    "주차장관리번호",

                    "주차장명",

                    "자치구",

                    "소재지지번주소",

                    "제공기관명"

                ]

                if col
                in duplicates.columns

            ]


            if cols:

                st.dataframe(

                    duplicates[
                        cols
                    ]
                    .sort_values(
                        "주차장관리번호"
                    ),

                    hide_index=
                    True,

                    width=
                    "stretch"

                )
