import streamlit as st
import pandas as pd
from datetime import datetime
import time
import json
import gspread
from google.oauth2.service_account import Credentials

# --- 페이지 설정 ---
st.set_page_config(page_title="인터뷰 레코더", layout="wide")

# 스타일 커스텀
st.markdown("""
<style>
    .stTextArea textarea { font-size: 14px; background-color: #f9f9f9; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; }
    div[data-testid="stMetricValue"] { font-size: 18px; }
</style>
""", unsafe_allow_html=True)

# --- 1. 구글 시트 연결 (강제 수술 모드) ---
# 캐싱을 써서 새로고침해도 연결 유지
@st.cache_resource
def get_google_sheet():
    try:
        # 1. Secrets에서 JSON 문자열 가져오기
        # [connections.gsheets] 안에 있어도 되고, 그냥 최상위에 있어도 찾도록 로직 구성
        if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
            secrets_str = st.secrets["connections"]["gsheets"]["service_account"]
        else:
            # 혹시 형식이 다를 경우를 대비해 바로 service_account 키를 찾음
            secrets_str = st.secrets["service_account"]

        # 2. 파이썬 딕셔너리로 변환
        creds_dict = json.loads(secrets_str)

        # 🚨 [핵심 수술] private_key의 줄바꿈 문자(\n)를 진짜 엔터로 치환
        # 이게 안 되면 401 무조건 뜸
        creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

        # 3. 인증 범위 설정
        scopes = [
            "[https://www.googleapis.com/auth/spreadsheets](https://www.googleapis.com/auth/spreadsheets)",
            "[https://www.googleapis.com/auth/drive](https://www.googleapis.com/auth/drive)"
        ]

        # 4. 인증 객체 생성
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)

        # 5. 시트 열기
        if "connections" in st.secrets:
            url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        else:
            url = st.secrets["spreadsheet"]
            
        sh = client.open_by_url(url)
        return sh

    except Exception as e:
        st.error(f"🔥 연결 실패! 에러 내용을 찍어주세요: {e}")
        return None

# 연결 시도
sh = get_google_sheet()

if not sh:
    st.stop()

# 워크시트 가져오기 (이름 "시트1" 확인 필수)
try:
    worksheet = sh.worksheet("시트1")
except:
    st.error("탭 이름이 '시트1'이 아닙니다. 구글 시트 아래 탭 이름을 확인해주세요.")
    st.stop()

# 데이터 프레임 로드
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# 필수 컬럼 정의 및 빈 데이터 처리
required_cols = [
    '지역', '이름', '직급', '직급 코드', '소속', 
    '업무', '업무 카테고리', '참여의지', '인터뷰내용'
]

if df.empty:
    # 데이터가 아예 없으면 컬럼만 있는 빈 프레임 생성
    df = pd.DataFrame(columns=required_cols)
else:
    # 없는 컬럼 추가
    for col in required_cols:
        if col not in df.columns:
            df[col] = ""

df = df.fillna("")

# --- [사이드바] 직원 검색 및 선택 ---
with st.sidebar:
    st.header("👥 인터뷰 대상자")
    
    if df.empty:
        st.warning("데이터가 없습니다.")
        st.stop()

    search_query = st.text_input("검색 (이름/소속)", placeholder="이름 입력...")
    
    # 문자열로 변환 후 검색
    if search_query:
        mask = df.apply(lambda x: search_query in str(x['이름']) or search_query in str(x['소속']), axis=1)
        filtered_df = df[mask]
    else:
        filtered_df = df

    if filtered_df.empty:
        st.warning("검색 결과가 없습니다.")
        st.stop()

    # 라디오 버튼 옵션 생성
    options = filtered_df.apply(lambda x: f"{x['이름']} ({x['소속']})", axis=1).tolist()
    selected_option = st.radio("대상자 선택", options, label_visibility="collapsed")
    
    # 선택된 사람 찾기
    selected_name = selected_option.split(" (")[0]
    selected_dept = selected_option.split(" (")[1][:-1]
    
    # 인덱스 찾기 (Pandas Index가 아니라 gspread의 행 번호를 위해)
    # 데이터프레임에서의 인덱스
    mask = (df['이름'] == selected_name) & (df['소속'] == selected_dept)
    person_row = df[mask].iloc[0]
    person_idx = df[mask].index[0] 
    
    # 실제 구글 시트에서의 행 번호 (헤더가 1번이므로 +2)
    # gspread는 1부터 시작, get_all_records는 헤더 제외하고 가져옴. 
    # 안전하게 다시 매칭하는 로직 필요하지만 일단 간단히 계산
    gsheet_row_num = person_idx + 2 

# --- [메인 화면] ---
st.subheader(f"📌 {person_row['이름']} {person_row['직급']} 인터뷰")

col1, col2, col3, col4, col5 = st.columns(5)
with col1: st.info(f"**소속**\n\n{person_row['소속']}")
with col2: st.info(f"**지역**\n\n{person_row['지역']}")
with col3: st.info(f"**업무**\n\n{person_row['업무']}")
with col4: st.info(f"**참여의지**\n\n{person_row['참여의지']}")
with col5: st.info(f"**시간**\n\n{datetime.now().strftime('%H:%M')}")

st.markdown("---")

# JSON 파싱
saved_content = person_row['인터뷰내용']
answers = {}
try:
    if str(saved_content).strip():
        answers = json.loads(str(saved_content))
except:
    answers = {"7-1": str(saved_content)}

# --- 인터뷰 폼 ---
st.markdown("### 📝 인터뷰 질문 리스트")

with st.form(key='interview_form'):
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "1. Daily", "2. Weekly", "3. 중요 비정기", 
        "4. 문서/협업", "5. 우회행동", "6. AI 활용", "7. 기타"
    ])

    def create_q(tab, key, question):
        with tab:
            st.markdown(f"**{key}. {question}**")
            return st.text_area(label=question, value=answers.get(key, ""), height=100, key=f"k_{key}", label_visibility="collapsed")

    # 질문 리스트
    ans = {}
    ans["1-1"] = create_q(tab1, "1-1", "출근 후 EP에서 가장 먼저 하는 작업")
    ans["1-2"] = create_q(tab1, "1-2", "매일 반복 작업 중 자동화/간소화가 필요한 것")
    ans["1-3"] = create_q(tab1, "1-3", "퇴근 전(또는 특정 시간) 반드시 확인하는 정보")
    
    ans["2-1"] = create_q(tab2, "2-1", "EP에서 주 단위로 처리하는 작업")
    ans["2-2"] = create_q(tab2, "2-2", "매주 반복 작업 중 자동화/간소화가 필요한 부분")
    
    ans["3-1"] = create_q(tab3, "3-1", "비정기적이지만 중요도가 높은 업무")
    ans["3-2"] = create_q(tab3, "3-2", "위 업무 수행 시 사용하는 EP 기능 또는 앱")
    ans["3-3"] = create_q(tab3, "3-3", "업무 과정의 어려움이나 복잡한 부분")
    
    ans["4-1"] = create_q(tab4, "4-1", "EP시스템별 자주 겪는 어려움")
    ans["4-2"] = create_q(tab4, "4-2", "기능 부족으로 다른 방식 이용 경험")
    
    ans["5-1"] = create_q(tab5, "5-1", "EP 기능 부족으로 추가 사용하는 도구")
    ans["5-2"] = create_q(tab5, "5-2", "해당 도구를 사용하게 된 이유")
    
    ans["6-1"] = create_q(tab6, "6-1", "사내 AI 기능 중 실제로 사용해본 것")
    ans["6-2"] = create_q(tab6, "6-2", "기대에 미치지 못했던 기능과 이유")
    ans["6-3"] = create_q(tab6, "6-3", "외부 서비스 중 EP 도입 희망 기능")
    ans["6-4"] = create_q(tab6, "6-4", "AI 지원 시 가장 도움될 업무 영역")
    
    ans["7-1"] = create_q(tab7, "7-1", "EP 개선 요청 사항")
    ans["7-2"] = create_q(tab7, "7-2", "PC와 모바일 환경 사용 비율")

    st.markdown("---")
    submit = st.form_submit_button("💾 저장하기", use_container_width=True)

    if submit:
        try:
            # JSON 변환
            json_str = json.dumps(ans, ensure_ascii=False)
            
            # gspread로 업데이트 (API 직접 호출)
            # '인터뷰내용' 컬럼 찾기 (헤더에서)
            headers = worksheet.row_values(1)
            try:
                col_idx = headers.index('인터뷰내용') + 1
            except:
                st.error("'인터뷰내용' 컬럼이 시트에 없습니다.")
                st.stop()
                
            # 셀 업데이트 (행, 열, 값)
            worksheet.update_cell(gsheet_row_num, col_idx, json_str)
            
            st.toast("✅ 저장 성공! (Google Sheets 반영 완료)")
            time.sleep(1)
            st.rerun()
            
        except Exception as e:
            st.error(f"저장 실패: {e}")
