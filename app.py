from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px

# 화면을 넓게 설정
st.set_page_config(page_title="서울 공영주차장 대시보드", layout="wide")

st.title("서울 공영주차장 대시보드")

# app.py가 있는 폴더
HERE = Path(__file__).parent

# 전국 주차장 데이터 읽기
data = pd.read_csv(
    HERE / "parking.csv",
    encoding="cp949",
    low_memory=False
)

# 주소가 비어 있으면 빈 문자열로 처리
road_address = data["소재지도로명주소"].fillna("")
lot_address = data["소재지지번주소"].fillna("")

# 도로명주소 또는 지번주소가 서울특별시로 시작하는지 확인
is_seoul = (
    road_address.str.startswith("서울특별시")
    | lot_address.str.startswith("서울특별시")
)

# 공영주차장인지 확인
is_public = data["주차장구분"] == "공영"

# 서울 소재 공영주차장만 선택
seoul = data.loc[is_seoul & is_public].copy()

# 도로명주소가 없으면 지번주소 사용
address = seoul["소재지도로명주소"].fillna(
    seoul["소재지지번주소"]
)

# 주소에서 자치구 이름 추출
seoul["자치구"] = address.str.extract(r"서울특별시\s+(\S+구)")

# 확인용 출력은 접히는 상자에 모으기
with st.expander("데이터 점검 내용 보기", expanded=False):
    st.write("전국 주차장 데이터 건수:", len(data))
    st.write("서울 공영주차장 데이터 행 수 — 중복 정리 전:", len(seoul))
    st.dataframe(seoul.head(10))

    st.write("자치구 수:", seoul["자치구"].nunique())

    st.dataframe(
        seoul[["주차장명", "자치구", "주차구획수", "요금정보"]].head(10)
    )

    # 관리번호가 반복되는 행을 모두 선택
    duplicates = seoul[
        seoul.duplicated(subset="주차장관리번호", keep=False)
    ]

    st.subheader("관리번호 중복 확인")
    st.write("관리번호가 반복되는 행 수:", len(duplicates))

    st.dataframe(
        duplicates[
            [
                "주차장관리번호",
                "주차장명",
                "자치구",
                "소재지지번주소",
                "제공기관명",
            ]
        ].sort_values("주차장관리번호")
    )

st.subheader("자치구별 공영주차장 조회")

# 자치구 이름을 가나다순으로 정렬
districts = sorted(seoul["자치구"].dropna().unique())

# 왼쪽 사이드바에 자치구 선택 메뉴 만들기
selected_district = st.sidebar.selectbox(
    "자치구 선택",
    districts,
    index=districts.index("동대문구")
)

# 선택한 자치구의 행만 남기기
view = seoul.loc[
    seoul["자치구"] == selected_district
].copy()

# 선택한 데이터에서 지표 계산
record_count = len(view)
total_spaces = view["주차구획수"].sum()
free_count = (view["요금정보"] == "무료").sum()

# 숫자 카드 3개를 나란히 배치
c1, c2, c3 = st.columns(3)

c1.metric("주차장 데이터 건수", f"{record_count:,}건")
c2.metric("주차구획수 합계", f"{total_spaces:,}면")
c3.metric("무료 주차장 데이터 건수", f"{free_count:,}건")

st.caption("원자료의 각 행을 1건으로 집계했으며, 동일 시설의 중복 등록이 포함될 수 있습니다. '혼합'은 무료 건수에서 제외합니다.")

# 선택한 자치구의 상세 표
with st.expander("선택한 자치구의 주차장 목록 보기"):
    st.dataframe(view[["주차장명", "자치구", "주차구획수", "요금정보"]], hide_index=True, width="stretch")

# 첫 번째 그래프: 주차구획수 상위 10건
st.subheader(f"{selected_district} 주차구획수 상위 10건")

top10 = view.nlargest(10, "주차구획수")

fig = px.bar(
    top10,
    x="주차구획수",
    y="주차장명",
    orientation="h",
    labels={
        "주차구획수": "주차구획수 (면)",
        "주차장명": "주차장"
    },
    hover_data=["요금정보"]
)

fig.update_yaxes(categoryorder="total ascending")
fig.update_xaxes(rangemode="tozero")

# 막대 색상과 숫자 표시
fig.update_traces(marker_color="#245580", texttemplate="%{x:,.0f}면", textposition="outside", cliponaxis=False)

# 배경과 글자, 여백 설정
fig.update_layout(template="plotly_white", height=480, font=dict(size=14), margin=dict(l=20, r=90, t=20, b=40))

# 가로축의 격자를 연하게 표시
fig.update_xaxes(showgrid=True, gridcolor="#E8EDF2", zeroline=False)

# 세로축 격자와 제목 숨기기
fig.update_yaxes(showgrid=False, title_text="")

st.plotly_chart(fig, width="stretch")

# 두 번째 그래프: 주차장 규모 분포
st.subheader(f"{selected_district} 주차장 규모 분포")

fig_size = px.histogram(view, x="주차구획수", nbins=20)

fig_size.update_layout(
    xaxis_title="주차구획수 (면)",
    yaxis_title="주차장 데이터 건수"
)

fig_size.update_yaxes(rangemode="tozero")

# 막대를 청록색으로, 경계는 흰색으로 표시
fig_size.update_traces(marker_color="#278C88", marker_line_color="white", marker_line_width=1)

# 배경과 글자 크기 통일
fig_size.update_layout(template="plotly_white", height=400, font=dict(size=14), bargap=0, margin=dict(l=20, r=20, t=30, b=40))

# 축과 격자 정리
fig_size.update_xaxes(showgrid=False, rangemode="tozero", tick0=0, dtick=10)
fig_size.update_traces(xbins=dict(start=0, size=10), autobinx=False)
fig_size.update_yaxes(rangemode="tozero", tickformat=",d", gridcolor="#E8EDF2")

st.plotly_chart(fig_size, width="stretch")

# 세 번째 그래프: 요금 유형별 주차장 데이터 건수
st.subheader(f"{selected_district} 요금 유형별 주차장 데이터 건수")

fee_counts = view.groupby("요금정보").size()
fee_counts = fee_counts.reindex(["유료", "무료", "혼합"], fill_value=0)
fee_counts = fee_counts.reset_index(name="주차장 데이터 건수")

fee_colors = {
    "유료": "#0072B2",
    "무료": "#009E73",
    "혼합": "#E69F00"
}

fig_fee = px.bar(
    fee_counts,
    x="요금정보",
    y="주차장 데이터 건수",
    color="요금정보",
    text="주차장 데이터 건수",
    color_discrete_map=fee_colors
)

fig_fee.update_layout(
    xaxis_title="요금 유형",
    yaxis_title="주차장 데이터 건수",
    showlegend=False
)

fig_fee.update_yaxes(rangemode="tozero", tickformat=",d", gridcolor="#E8EDF2")

# 막대 위에 건수 표시
fig_fee.update_traces(texttemplate="%{y:,.0f}건", textposition="outside", cliponaxis=False)

# 배경, 글자 크기, 여백 통일
fig_fee.update_layout(template="plotly_white", height=400, font=dict(size=14), bargap=0.45, margin=dict(l=20, r=20, t=40, b=40))

# 가로축 격자 숨기기
fig_fee.update_xaxes(showgrid=False)

st.plotly_chart(fig_fee, width="stretch")

# 주차장 위치 지도
st.subheader(f"{selected_district} 공영주차장 위치")

map_data = view[["위도", "경도"]].copy()

# 좌표를 숫자로 변환
map_data["위도"] = pd.to_numeric(map_data["위도"], errors="coerce")
map_data["경도"] = pd.to_numeric(map_data["경도"], errors="coerce")

# 좌표가 없는 행은 지도에서만 제외
map_data = map_data.dropna(subset=["위도", "경도"])

# 지도에서 사용하는 열 이름으로 변경
map_data = map_data.rename(
    columns={"위도": "latitude", "경도": "longitude"}
)

if map_data.empty:
    st.info("선택한 자치구에는 표시할 좌표가 없습니다.")
else:
    st.map(map_data)

st.caption(f"선택한 데이터 {len(view)}건 중 좌표가 있는 {len(map_data)}건을 지도에 표시합니다.")

# 선택한 자치구 데이터 다운로드
st.subheader("선택한 자치구 데이터 다운로드")

csv_data = view.to_csv(index=False).encode("utf-8-sig")

st.download_button(
    label="선택한 자치구 CSV 다운로드",
    data=csv_data,
    file_name=f"seoul_parking_{selected_district}.csv",
    mime="text/csv"
)

st.divider()
st.subheader("데이터 출처와 해석 안내")

st.markdown("출처: [공공데이터포털 — 전국주차장정보표준데이터](https://www.data.go.kr/data/15012896/standard.do)")

st.write("분석 대상: 도로명주소 또는 지번주소가 서울특별시로 시작하고, 주차장구분이 공영인 등록 기록입니다.")

st.write("집계 기준: 주차장 데이터 건수는 원자료의 행 수이며, 주차구획수 합계는 각 행의 주차 칸 수를 더한 값입니다. 동일 시설이 중복 등록돼 있다면 건수와 합계가 실제보다 커질 수 있습니다.")

st.write("요금 구분: 원자료의 유료·무료·혼합 분류를 사용하며, 혼합은 무료에 포함하지 않습니다.")

st.write("중복 처리: 같은 관리번호에 서로 다른 이름과 주소가 있어, 관리번호만으로 기록을 삭제하지 않았습니다. 동일 시설의 중복 등록 여부는 추가 확인이 필요합니다.")

st.write("해석의 한계: 지역별 자료의 누락과 갱신 시점 차이가 있을 수 있으므로, 주차장 데이터 건수를 실제 전체 주차장 수로 단정할 수 없습니다.")

st.write("지도: 좌표가 없는 기록은 지도에서만 제외했습니다. 실시간 빈자리 정보는 제공하지 않습니다.")

st.caption(f"선택한 자치구의 데이터 기준일 범위: {view['데이터기준일자'].min()} ~ {view['데이터기준일자'].max()}")