import streamlit as st
import pandas as pd
from datetime import datetime
import time
import json
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="인터뷰 레코더", layout="wide")

st.markdown("""
<style>
    .stTextArea textarea { font-size: 14px; background-color: #f9f9f9; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; }
</style>
""", unsafe_allow_html=True)

# --- 구글 시트 연결 (개별 Secrets 방식) ---
@st.cache_resource
def get_google_sheet():
    try:
        # Secrets 전체를 딕셔너리로 가져옴
        creds_dict = dict(st.secrets["connections"]["gsheets"])
        
        # spreadsheet URL 분리
        if "spreadsheet" in creds_dict:
            sheet_url = creds_dict.pop("spreadsheet")
        
        # 🚨 [핵심] private_key 줄바꿈 문자(\n) 강제 교정
        # TOML에서 가져올 때 문자열 \n으로 들어오는 것을 실제 엔터로 치환
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open_by_url(sheet_url)

    except Exception as e:
        st.error(f"🔥 연결 에러: {e}")
        return None

# 연결 실행
sh = get_google_sheet()
if not sh: st.stop()

# 워크시트 로드
try:
    worksheet = sh.worksheet("시트1")
except:
    st.error("'시트1' 탭을 찾을 수 없습니다.")
    st.stop()

# 데이터 로드
df = pd.DataFrame(worksheet.get_all_records())
required_cols = ['지역', '이름', '직급', '직급 코드', '소속', '업무', '업무 카테고리', '참여의지', '인터뷰내용']

if df.empty:
    df = pd.DataFrame(columns=required_cols)
else:
    for col in required_cols:
        if col not in df.columns: df[col] = ""

df = df.fillna("")

# --- 사이드바 ---
with st.sidebar:
    st.header("👥 인터뷰 대상자")
    if df.empty: st.stop()
    
    search = st.text_input("검색", placeholder="이름/소속")
    if search:
        mask = df.apply(lambda x: search in str(x['이름']) or search in str(x['소속']), axis=1)
        filtered = df[mask]
    else:
        filtered = df
        
    if filtered.empty: st.stop()
    
    opts = filtered.apply(lambda x: f"{x['이름']} ({x['소속']})", axis=1).tolist()
    sel = st.radio("선택", opts, label_visibility="collapsed")
    
    s_name = sel.split(" (")[0]
    s_dept = sel.split(" (")[1][:-1]
    
    mask = (df['이름'] == s_name) & (df['소속'] == s_dept)
    row = df[mask].iloc[0]
    # gspread 행 번호 계산 (헤더1 + 인덱스 + 1(0부터시작보정) = +2)
    row_num = df[mask].index[0] + 2

# --- 메인 ---
st.subheader(f"📌 {row['이름']} {row['직급']}")
c1,c2,c3,c4,c5 = st.columns(5)
c1.info(f"**소속**: {row['소속']}")
c2.info(f"**지역**: {row['지역']}")
c3.info(f"**업무**: {row['업무']}")
c4.info(f"**의지**: {row['참여의지']}")
c5.info(datetime.now().strftime('%H:%M'))

# 내용 파싱
try:
    ans = json.loads(str(row['인터뷰내용'])) if str(row['인터뷰내용']).strip() else {}
except:
    ans = {"7-1": str(row['인터뷰내용'])}

# 폼
st.markdown("---")
with st.form("form"):
    tabs = st.tabs(["Daily", "Weekly", "중요비정기", "문서/협업", "우회행동", "AI활용", "기타"])
    
    def q(t, k, q_txt):
        with t:
            st.markdown(f"**{k} {q_txt}**")
            return st.text_area("-", value=ans.get(k, ""), height=100, key=k, label_visibility="collapsed")

    new_ans = {}
    new_ans["1-1"] = q(tabs[0], "1-1", "출근 후 가장 먼저 하는 작업")
    new_ans["1-2"] = q(tabs[0], "1-2", "매일 반복 중 자동화 필요")
    new_ans["1-3"] = q(tabs[0], "1-3", "퇴근 전 필수 확인")
    
    new_ans["2-1"] = q(tabs[1], "2-1", "주 단위 작업")
    new_ans["2-2"] = q(tabs[1], "2-2", "매주 반복 중 자동화 필요")
    
    new_ans["3-1"] = q(tabs[2], "3-1", "비정기 중요 업무")
    new_ans["3-2"] = q(tabs[2], "3-2", "사용하는 기능/앱")
    new_ans["3-3"] = q(tabs[2], "3-3", "어려움/복잡한 점")
    
    new_ans["4-1"] = q(tabs[3], "4-1", "시스템별 어려움")
    new_ans["4-2"] = q(tabs[3], "4-2", "다른 방식 사용 경험")
    
    new_ans["5-1"] = q(tabs[4], "5-1", "추가 사용 도구")
    new_ans["5-2"] = q(tabs[4], "5-2", "사용 이유")
    
    new_ans["6-1"] = q(tabs[5], "6-1", "사내 AI 사용 경험")
    new_ans["6-2"] = q(tabs[5], "6-2", "기대에 못 미친 이유")
    new_ans["6-3"] = q(tabs[5], "6-3", "도입 희망 기능")
    new_ans["6-4"] = q(tabs[5], "6-4", "AI 도움 필요한 영역")
    
    new_ans["7-1"] = q(tabs[6], "7-1", "개선 요청")
    new_ans["7-2"] = q(tabs[6], "7-2", "PC/모바일 비율")

    if st.form_submit_button("💾 저장", use_container_width=True):
        try:
            # 컬럼 위치 찾기
            headers = worksheet.row_values(1)
            col_idx = headers.index('인터뷰내용') + 1
            # 업데이트
            worksheet.update_cell(row_num, col_idx, json.dumps(new_ans, ensure_ascii=False))
            st.toast("✅ 저장 완료")
            time.sleep(1)
            st.rerun()
        except Exception as e:
            st.error(f"저장 실패: {e}")
