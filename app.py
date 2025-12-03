import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import time
import json

# --- 페이지 설정 ---
st.set_page_config(page_title="인터뷰 레코더", layout="wide")

# 스타일 커스텀
st.markdown("""
<style>
    .stTextArea textarea {
        font-size: 14px;
        line-height: 1.5;
        background-color: #f9f9f9;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 4px 4px 0px 0px;
        gap: 1px;
        padding-top: 10px;
        padding-bottom: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff;
        border-bottom: 2px solid #ff4b4b;
    }
    div[data-testid="stMetricValue"] {
        font-size: 18px;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. 구글 시트 연결 및 데이터 로드 ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    # worksheet 이름이 "시트1" 인지 꼭 확인하세요!
    df = conn.read(worksheet="시트1", ttl=0)
    
    # 필수 컬럼 정의 (시트 헤더에 이 내용들이 있어야 합니다)
    required_cols = [
        '지역', '이름', '직급', '직급 코드', '소속', 
        '업무', '업무 카테고리', '참여의지', '인터뷰내용'
    ]
    
    # 없는 컬럼은 빈 값으로 생성하여 에러 방지
    for col in required_cols:
        if col not in df.columns:
            df[col] = ""
            
    df = df.fillna("")

except Exception as e:
    st.error(f"🚨 구글 시트 연결 실패! Secrets 설정을 확인해주세요.\n\n에러 메시지: {e}")
    st.stop()

# --- [사이드바] 직원 검색 및 선택 ---
with st.sidebar:
    st.header("👥 인터뷰 대상자")
    
    if df.empty:
        st.warning("데이터가 없습니다. 구글 시트를 확인해주세요.")
        st.stop()

    # 검색 기능
    search_query = st.text_input("검색 (이름/소속)", placeholder="이름 입력...")
    
    # 검색 필터링
    if search_query:
        filtered_df = df[
            df['이름'].astype(str).str.contains(search_query) | 
            df['소속'].astype(str).str.contains(search_query)
        ]
    else:
        filtered_df = df

    if filtered_df.empty:
        st.warning("검색 결과가 없습니다.")
        st.stop()

    # 라디오 버튼 (이름 + 소속으로 구분)
    # apply 함수 내에서 모든 값을 문자열로 변환하여 에러 방지
    options = filtered_df.apply(lambda x: f"{str(x['이름'])} ({str(x['소속'])})", axis=1).tolist()
    selected_option = st.radio("대상자 선택", options, label_visibility="collapsed")
    
    # 선택값 파싱
    selected_name = selected_option.split(" (")[0]
    selected_dept = selected_option.split(" (")[1][:-1]
    
    # 해당 직원 데이터 찾기
    mask = (df['이름'] == selected_name) & (df['소속'] == selected_dept)
    if not mask.any():
        st.error("데이터 매칭 오류. 새로고침 해주세요.")
        st.stop()
        
    person_row = df[mask].iloc[0]
    person_index = df[mask].index[0]

# --- [메인 화면] ---

# 1. 상단 정보 패널
st.subheader(f"📌 {person_row['이름']} {person_row['직급']} 인터뷰")

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.info(f"**소속**\n\n{person_row['소속']}")
with col2:
    st.info(f"**지역**\n\n{person_row['지역']}")
with col3:
    st.info(f"**업무**\n\n{person_row['업무']}")
with col4:
    st.info(f"**참여의지**\n\n{person_row['참여의지']}")
with col5:
    st.info(f"**현재 시간**\n\n{datetime.now().strftime('%H:%M')}")

st.markdown("---")

# 2. 기존 인터뷰 데이터 파싱 (JSON)
saved_content = person_row['인터뷰내용']
answers = {}
try:
    if saved_content and str(saved_content).strip():
        answers = json.loads(str(saved_content))
except:
    # JSON 파싱 실패 시 (기존 일반 텍스트 데이터가 있는 경우)
    answers = {"7-1": str(saved_content)}

# --- 3. 인터뷰 질문 탭 구성 ---
st.markdown("### 📝 인터뷰 질문 리스트")

with st.form(key='interview_form'):
    
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "1. Daily", "2. Weekly", "3. 중요 비정기", 
        "4. 문서/협업", "5. 우회행동", "6. AI 활용", "7. 기타"
    ])

    # 질문 생성 함수
    def create_q(tab, key, question):
        with tab:
            st.markdown(f"**{key}. {question}**")
            return st.text_area(
                label=question,
                value=answers.get(key, ""),
                height=100,
                key=f"input_{key}",
                label_visibility="collapsed"
            )

    # 1. Daily
    ans_1_1 = create_q(tab1, "1-1", "출근 후 EP에서 가장 먼저 하는 작업")
    ans_1_2 = create_q(tab1, "1-2", "매일 반복 작업 중 자동화/간소화가 필요한 것")
    ans_1_3 = create_q(tab1, "1-3", "퇴근 전(또는 특정 시간) 반드시 확인하는 정보")

    # 2. Weekly
    ans_2_1 = create_q(tab2, "2-1", "EP에서 주 단위로 처리하는 작업")
    ans_2_2 = create_q(tab2, "2-2", "매주 반복 작업 중 자동화/간소화가 필요한 부분")

    # 3. 비정기 중요 업무
    ans_3_1 = create_q(tab3, "3-1", "비정기적이지만 반드시 처리해야 하고 중요도가 높은 업무")
    ans_3_2 = create_q(tab3, "3-2", "위 업무 수행 시 사용하는 EP 기능 또는 앱")
    ans_3_3 = create_q(tab3, "3-3", "이 업무 과정에서 겪는 어려움이나 복잡한 부분")

    # 4. 문서/결재/협업
    ans_4_1 = create_q(tab4, "4-1", "EP시스템별 자주 겪는 어려움")
    ans_4_2 = create_q(tab4, "4-2", "기능 부족으로 다른 방식(메신저 등)을 이용하는 경험")

    # 5. 우회 행동
    ans_5_1 = create_q(tab5, "5-1", "EP 기능이 부족하여 추가로 사용하는 도구나 방법")
    ans_5_2 = create_q(tab5, "5-2", "해당 도구 또는 방법을 사용하게 된 이유")

    # 6. AI 관련 경험
    ans_6_1 = create_q(tab6, "6-1", "회사 제공 AI 기능 중 실제로 사용해본 것")
    ans_6_2 = create_q(tab6, "6-2", "사용했지만 기대에 미치지 못했던 기능과 이유")
    ans_6_3 = create_q(tab6, "6-3", "외부 서비스 중 EP에도 있었으면 좋겠다고 느낀 기능")
    ans_6_4 = create_q(tab6, "6-4", "EP 내에서 AI가 지원해주면 가장 도움이 될 업무 영역")

    # 7. 기타
    ans_7_1 = create_q(tab7, "7-1", "EP에서 꼭 개선되었으면 하는 부분 (자유)")
    ans_7_2 = create_q(tab7, "7-2", "PC와 모바일 환경 사용 비율")

    st.markdown("---")
    
    # 저장 버튼
    col_sub1, col_sub2 = st.columns([5, 1])
    with col_sub2:
        submit_button = st.form_submit_button(label='💾 저장하기', use_container_width=True)

    if submit_button:
        # 데이터 수집
        new_answers = {
            "1-1": ans_1_1, "1-2": ans_1_2, "1-3": ans_1_3,
            "2-1": ans_2_1, "2-2": ans_2_2,
            "3-1": ans_3_1, "3-2": ans_3_2, "3-3": ans_3_3,
            "4-1": ans_4_1, "4-2": ans_4_2,
            "5-1": ans_5_1, "5-2": ans_5_2,
            "6-1": ans_6_1, "6-2": ans_6_2, "6-3": ans_6_3, "6-4": ans_6_4,
            "7-1": ans_7_1, "7-2": ans_7_2
        }
        
        try:
            # JSON 형태로 변환하여 시트에 저장 (한글 깨짐 방지)
            json_data = json.dumps(new_answers, ensure_ascii=False)
            
            # 데이터프레임 업데이트
            df.at[person_index, '인터뷰내용'] = json_data
            
            # 구글 시트에 쓰기
            conn.update(worksheet="시트1", data=df)
            
            st.toast(f"✅ {person_row['이름']}님의 인터뷰 내용이 저장되었습니다!")
            time.sleep(1)
            st.rerun()
            
        except Exception as e:
            st.error(f"저장 중 오류가 발생했습니다: {e}")
