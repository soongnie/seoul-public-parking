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
        "최소 주차면수",
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
        "요금 유형·최소 주차면수 필터는 '주차장 찾기'와 "
        "'데이터·한계'의 목록·CSV 다운로드에 적용됩니다. "
        "상단 지표와 '선택 지역 분석'은 선택한 구 전체, "
        "'서울 전체 비교'는 서울 전체 등록 데이터를 사용합니다."
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
    "주차장 등록 건수",
    f"{int(summary_row['데이터건수']):,}건"
)

c1.caption(
    f"자치구 평균의 "
    f"{summary_row['건수_서울평균배율']:.2f}배"
)


c2.metric(
    "총 주차면수",
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
    "무료 비율",
    f"{summary_row['무료비율']:.1f}%"
)

c4.caption(
    f"자치구별 무료 비율 평균: "
    f"{city_mean_free_rate:.1f}%"
)



note(
    "주차장 등록 건수·총 주차면수·주차장 규모 중앙값·무료 비율을 함께 비교합니다. "
    "주차장 등록 건수는 원자료의 행 수이며, 동일 시설의 중복 등록이 포함될 수 있습니다."
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

    st.markdown(
        f"**조건에 맞는 주차장 등록 건수 {len(filtered_view):,}건 "
        f"· 지도 표시 {len(map_data):,}건**"
    )

    excluded_count = len(filtered_view) - len(map_data)

    if excluded_count > 0:
        st.caption(
            f"좌표 정보가 없거나 유효하지 않은 "
            f"{excluded_count:,}건은 지도에서 제외했습니다."
        )

    if not selected_fee_types:
        st.info("요금 유형을 하나 이상 선택해 주세요.")

    elif filtered_view.empty:
        st.info(
            "조건에 맞는 기록이 없습니다. "
            "최소 주차면수를 낮추거나 요금 유형을 추가해 주세요."
        )

    elif map_data.empty:
        st.info(
            "조건에 맞는 기록은 있지만, 지도에 표시할 유효한 좌표가 없습니다. "
            "'데이터·한계' 탭에서 목록을 확인해 주세요."
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
            "점 위에 마우스를 올리면 주차장명·주차면수·주소를 확인할 수 있습니다. "
            "같은 좌표의 기록은 점이 겹칠 수 있습니다."
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
        pass

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
            "주차장 등록 건수",
            "주차장 규모 중앙값",
            "무료 비율"
        ]

    )


    metric_map = {

        "총 주차면수":
        (
            "총주차면",
            "면"
        ),

        "주차장 등록 건수":
        (
            "데이터건수",
            "건"
        ),

        "주차장 규모 중앙값":
        (
            "중앙주차면",
            "면"
        ),

        "무료 비율":
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

    elif metric_col == "중앙주차면":
        text_template = "%{x:,.1f}"
        hover_template = (
            "%{y}<br>"
            "%{x:,.1f}면"
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

    st.caption(
        "요금 유형·최소 주차면수 필터와 관계없이, "
        "선택한 자치구의 전체 등록 기록을 분석합니다."
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
            hovertemplate=(
                "요금 유형: %{label}<br>"
                "주차장 등록 건수: %{value:,.0f}건<br>"
                "비율: %{percent:.1%}"
                "<extra></extra>"
            ),

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
                        "<br>주차장 등록 건수"
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

        st.markdown("#### 주차장 규모 분포")

        sizes = view["규모_면"].dropna()
        sizes = sizes.loc[np.isfinite(sizes)]

        if sizes.empty:
            st.info("유효한 주차구획수 정보가 없습니다.")

        else:
            # 상자와 경계선에 같은 사분위수 사용
            q1 = sizes.quantile(0.25)
            median = sizes.median()
            q3 = sizes.quantile(0.75)
            mean = sizes.mean()

            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            # 경계 안에 있는 실제 데이터로 수염 끝 계산
            inside = sizes.loc[
                sizes.between(lower_bound, upper_bound)
            ]

            lower_whisker = inside.min()
            upper_whisker = inside.max()

            # 경계 밖의 데이터
            outliers = sizes.loc[
                (sizes < lower_bound)
                | (sizes > upper_bound)
            ]

            box = go.Figure()

            box.add_trace(
                go.Box(
                    q1=[q1],
                    median=[median],
                    q3=[q3],
                    lowerfence=[lower_whisker],
                    upperfence=[upper_whisker],
                    mean=[mean],
                    y=[0],
                    orientation="h",
                    boxmean=True,
                    boxpoints=False,
                    fillcolor="rgba(32, 59, 96, 0.35)",
                    line_color=NAVY,
                    name=selected_district,
                    hoverinfo="skip"
                )
            )

            # 경계 밖의 기록은 점으로 표시
            if not outliers.empty:
                box.add_trace(
                    go.Scatter(
                        x=outliers.tolist(),
                        y=[0] * len(outliers),
                        mode="markers",
                        marker=dict(size=8, color=TEAL),
                        showlegend=False,
                        hovertemplate="%{x:,.0f}면<extra></extra>"
                    )
                )

            style(box, 320)

            # 평균 점선과 구별되도록 경계는 주황색 파선
            box.add_vline(
                x=lower_bound,
                line_dash="dash",
                line_color=ORANGE,
                annotation_text="하한 경계",
                annotation_position="top right"
            )

            box.add_vline(
                x=upper_bound,
                line_dash="dash",
                line_color=ORANGE,
                annotation_text="상한 경계",
                annotation_position="top left"
            )

            # 음수인 하한 경계도 화면에 표시
            axis_min = min(sizes.min(), lower_bound)
            axis_max = max(sizes.max(), upper_bound)
            padding = max((axis_max - axis_min) * 0.1, 5)

            box.update_xaxes(
                title="주차구획수 (면)",
                range=[
                    axis_min - padding,
                    axis_max + padding
                ],
                showgrid=True,
                gridcolor="#E8EDF2"
            )

            box.update_yaxes(
                showticklabels=False,
                showgrid=False,
                zeroline=False,
                range=[-0.6, 0.6]
            )

            box.update_layout(showlegend=False)

            show(box, "district_box")

            st.markdown(
                f"**최솟값:** {fmt_num(sizes.min(), '면')} · "
                f"**중앙값:** {fmt_num(median, '면')} · "
                f"**평균:** {fmt_num(mean, '면')} · "
                f"**최댓값:** {fmt_num(sizes.max(), '면')}"
            )

            insight(
                f"중앙값은 {fmt_num(median, '면')}이며, "
                f"중간 50%의 등록 기록은 약 "
                f"{fmt_num(q1, '면')}~"
                f"{fmt_num(q3, '면')} 범위입니다."
            )

            st.caption(
                "상자: 중간 50% · 실선: 중앙값 · 점선: 평균"
            )

            st.caption(
                f"주황색 파선: 이상치 판단 경계 "
                f"({lower_bound:.1f}~{upper_bound:.1f}면). "
                "경계 밖의 점도 오류를 뜻하는 것은 아닙니다."
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
                "주차장 등록 건수",
                "총 주차면수",
                "주차장 규모 중앙값",
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
        "outside",

        hovertemplate=(
            "%{x}<br>"
            "자치구 평균 대비 %{y:.2f}배"
            "<extra></extra>"
        )


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

    if not selected_fee_types:
        st.info("요금 유형을 하나 이상 선택해 주세요.")

    elif filtered_view.empty:
        st.info(
            "조건에 맞는 기록이 없습니다. "
            "최소 주차면수를 낮추거나 요금 유형을 추가해 주세요."
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

        mime="text/csv",
        disabled=filtered_view.empty

    )


    st.divider()


    st.markdown("### 데이터 출처와 해석 안내")

    st.markdown(
        "**출처** · 공공데이터포털 "
        "[전국주차장정보표준데이터]"
        "(https://www.data.go.kr/data/15012896/standard.do)"
    )

    st.markdown(
        "**분석 대상** · 도로명주소 또는 지번주소가 "
        "‘서울특별시’로 시작하고, 주차장구분이 ‘공영’인 기록입니다. "
        "자치구별 비교에는 주소에서 자치구를 확인할 수 있는 기록을 사용합니다."
    )

    st.markdown(
        "**집계 기준과 중복** · 주차장 등록 건수는 원자료의 행 수이며, "
        "총 주차면수는 유효한 주차구획수의 합계입니다. "
        "관리번호가 반복된다는 이유만으로 기록을 삭제하지 않았습니다. "
        "동일 시설이 중복 등록됐다면 주차장 등록 건수와 총 주차면수가 "
        "실제보다 커질 수 있습니다."
    )

    st.markdown(
        "**규모와 결측치** · 주차장 규모는 주차 칸 수이며, 단위는 ‘면’입니다. "
        "숫자로 변환할 수 없거나 음수인 값은 규모 집계에서 제외합니다. "
        "규모 정보가 없는 기록은 최소 주차구획수를 0으로 설정해도 "
        "지도·목록 등 필터 결과에서 제외됩니다."
    )

    st.markdown(
        "**요금 유형과 무료 비율** · 제공기관의 유료·무료·혼합 분류를 사용하며, "
        "그 외 값과 빈 값은 ‘기타·미상’으로 표시합니다. "
        "무료 비율은 해당 구의 전체 주차장 등록 건수 중 "
        "‘무료’로 등록된 건수가 차지하는 비율입니다. "
        "혼합은 무료에 포함하지 않으며, "
        "요금 유형만으로 실제 결제 금액이나 무료 이용 조건을 알 수는 없습니다."
    )

    st.markdown(
        "**자치구 평균 대비 배율** · 자치구별 지표를 같은 비중으로 평균 낸 뒤, "
        "선택한 구의 값을 그 평균으로 나눕니다. "
        "**1배는 평균, 0.5배는 평균의 절반, 2배는 평균의 두 배**입니다. "
        "주차장 규모 중앙값은 각 구의 중앙값을 평균 낸 값과, "
        "무료 비율은 각 구의 무료 비율을 평균 낸 값과 비교합니다. "
        "이때 주차장 등록 건수와 관계없이 각 구를 같은 비중으로 반영합니다."
    )

    st.markdown(
        "**박스플롯** · 상자는 중간 50% 구간이며, "
        "상자 안의 실선은 중앙값, 점선은 평균입니다. "
        "주황색 파선은 이상치 판단 경계"
        "(Q1−1.5×IQR, Q3+1.5×IQR)이고, IQR은 Q3−Q1입니다. "
        "수염은 경계 안에 있는 실제 관측값의 최솟값과 최댓값까지 이어집니다. "
        "경계 밖의 점이 반드시 오류를 뜻하지는 않으며, "
        "하한 경계가 음수여도 실제 규모가 음수라는 뜻은 아닙니다."
    )

    st.markdown(
        "**지도와 원자료 행** · 지도에는 필터 결과 중 "
        "위도·경도가 유효 범위 안에 있고 0이 아닌 기록만 표시합니다. "
        "이 검사가 실제 위치의 정확성을 보장하지는 않으며, "
        "같은 좌표의 점은 겹칠 수 있습니다. "
        "‘원자료행’은 헤더를 포함한 원자료 표에서 기록을 찾기 위한 번호로, "
        "시설 고유번호가 아닙니다."
    )

    st.markdown(
        "**데이터 기준일** · 각 기록의 정보가 기준으로 삼는 날짜입니다. "
        "아래 범위는 선택한 구 전체 기록의 가장 이른 기준일과 가장 늦은 기준일이며, "
        "분석 기간이나 파일 다운로드 날짜가 아닙니다."
    )

    if "데이터기준일자" in view.columns:
        dates = pd.to_datetime(
            view["데이터기준일자"],
            errors="coerce"
        ).dropna()

        if not dates.empty:
            st.caption(
                "선택한 구의 데이터 기준일 범위: "
                f"{dates.min():%Y-%m-%d} ~ {dates.max():%Y-%m-%d}"
            )

    st.info(
        "해석의 한계 · 중복 등록, 자료 누락, 기록별 기준일 차이로 "
        "실제 전체 현황과 차이가 있을 수 있습니다. "
        "주차장 등록 건수가 적은 구는 일부 기록만으로 비율이 크게 달라질 수 있습니다. "
        "주차 수요·실시간 빈자리·세부 요금 조건을 반영하지 않았으므로, "
        "주차면수가 많다고 주차 공간이 충분하다고 판단할 수는 없습니다. "
        "방문 전 실제 이용 가능 여부와 요금은 운영기관 안내를 확인해 주세요."
    )

    st.caption(
        "AI 활용: 코드 작성·시각화 설계·오류 수정·해석 문장 정리에 "
        "AI를 활용했습니다. 수치는 공개 CSV를 코드로 집계한 결과입니다."
    )



    # -------------------------------------------------
    # 데이터 점검
    # -------------------------------------------------

    with st.expander(
        "데이터 점검 내용 보기"
    ):

        st.write(
            "전국 주차장 등록 건수:",
            len(data)
        )


        st.write(
            "서울 공영주차장 등록 건수:",
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
