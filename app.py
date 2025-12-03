import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# --- 페이지 설정 ---
st.set_page_config(page_title="인터뷰 레코더", layout="wide")

# 스타일 커스텀 (선택사항: 입력창 글씨 크기 키우기 등)
st.markdown("""
<style>
    .stTextArea textarea {
        font-size: 16px;
        line-height: 1.5;
    }
    div[data-testid="stMetricValue"] {
        font-size: 20px;
    }
</style>
""", unsafe_allow_html=True)

# 1. 구글 시트 연결 및 데이터 로드
# (실제 실행 시 secrets.toml 설정이 필요합니다. 테스트용으로는 아래 csv 로드 부분 주석을 풀고 쓰세요)
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    df = conn.read(worksheet="시트1", ttl=0)
except:
    # (테스트용) 구글 시트 연결 안 될 경우 임시 데이터 생성
    data = {
        '이름': ['김철수', '이영희', '박지성', '손흥민'],
        '부서': ['인사팀', '개발팀', '영업팀', '마케팅팀'],
        '직급': ['대리', '과장', '사원', '팀장'],
        '주요업무': ['채용 관리', '백엔드 개발', '거래처 관리', '브랜드 전략'],
        '인터뷰내용': ['', '', '', '']
    }
    df = pd.DataFrame(data)

# --- [사이드바] 직원 리스트 (탭 역할) ---
with st.sidebar:
    st.header("👥 직원 리스트")
    # 라디오 버튼을 사용하여 탭처럼 직원 선택
    selected_name = st.radio(
        "인터뷰 대상자를 선택하세요",
        df['이름'].tolist(),
        label_visibility="collapsed" # 라벨 숨김 (깔끔하게)
    )

# 선택된 직원의 데이터 가져오기
person_row = df[df['이름'] == selected_name].iloc[0]
person_index = df[df['이름'] == selected_name].index[0]

# --- [메인 화면] 스케치 레이아웃 구현 ---

# 1. 헤더 영역 (이름, 업무 강조)
st.subheader(f"📌 {selected_name} {person_row['직급']} 인터뷰")

# 2. 정보 표시 영역 (컬럼으로 나누기)
# 스케치 상단: 이름/업무, 부서/시간 배치
col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

with col1:
    st.markdown("**이름**")
    st.info(f"{person_row['이름']}")

with col2:
    st.markdown("**부서**")
    st.info(f"{person_row['부서']}")

with col3:
    st.markdown("**주요 업무**")
    st.info(f"{person_row['주요업무']}")
    
with col4:
    st.markdown("**현재 시간**")
    # 실시간 현재 시간 표시 (시:분)
    now_time = datetime.now().strftime("%H:%M")
    st.info(f"{now_time}")

st.markdown("---")

# 3. 회의록 작성 영역 (넓은 박스)
st.markdown("### 📝 회의록")

with st.form(key='interview_form'):
    # 기존 내용 불러오기 (없으면 빈칸)
    current_notes = person_row['인터뷰내용'] if pd.notna(person_row['인터뷰내용']) else ""
    
    # 스케치의 큰 사각형 부분
    new_notes = st.text_area(
        label="내용을 입력하세요",
        value=current_notes,
        height=400, # 높이를 충분히 주어 스케치처럼 크게 만듦
        placeholder="자유롭게 인터뷰 내용을 작성하세요...",
        label_visibility="collapsed" # 라벨 숨겨서 깔끔하게
    )
    
    # 우측 하단 저장 버튼 배치
    col_submit = st.columns([6, 1]) # 버튼을 오른쪽 끝으로 밀기 위한 여백
    with col_submit[1]:
        submit_button = st.form_submit_button(label='💾 저장하기', use_container_width=True)

    if submit_button:
        # 1. 데이터프레임 업데이트
        df.at[person_index, '인터뷰내용'] = new_notes
        
        # 2. 구글 시트에 업데이트 (연결되어 있을 경우)
        try:
            conn.update(worksheet="시트1", data=df)
            st.toast(f"✅ {selected_name}님의 인터뷰 내용이 저장되었습니다!")
        except:
             st.toast("⚠️ (테스트 모드) 내용이 임시 저장되었습니다.")
        
        # 3. 화면 리프레시 (최신 내용 반영)
        # st.rerun() # 필요시 주석 해제
