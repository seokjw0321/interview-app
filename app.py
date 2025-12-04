import streamlit as st
import pandas as pd
from datetime import datetime
import time
import json
import gspread
from google.oauth2.service_account import Credentials
import pytz # 한국 시간 처리를 위해 추가

st.set_page_config(page_title="인터뷰 레코더", layout="wide")

# --- 스타일 커스텀 (카드 디자인 통일) ---
st.markdown("""
<style>
    .stTextArea textarea { font-size: 14px; background-color: #f9f9f9; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; }
    
    /* 상단 정보 카드 스타일 */
    .info-card {
        background-color: #F0F2F6;
        padding: 15px;
        border-radius: 8px;
        text-align: center;
        height: 100px; /* 높이 고정 */
        display: flex;
        flex-direction: column;
        justify_content: center;
        align-items: center;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    .info-label {
        font-size: 12px;
        color: #555;
        margin-bottom: 5px;
        font-weight: 600;
    }
    .info-value {
        font-size: 16px;
        font-weight: bold;
        color: #31333F;
        word-break: keep-all; /* 단어 단위 줄바꿈 */
        line-height: 1.2;
    }
</style>
""", unsafe_allow_html=True)

# --- 구글 시트 연결 ---
@st.cache_resource
def get_google_sheet():
    try:
        conn_secrets = st.secrets["connections"]["gsheets"]
        if "service_account" in conn_secrets:
            # 개별 입력 방식 등 유연하게 처리
            try:
                creds_dict = json.loads(conn_secrets["service_account"], strict=False)
            except:
                creds_dict = dict(conn_secrets)
        else:
            creds_dict = dict(conn_secrets)
            
        # URL 분리
        if "spreadsheet" in creds_dict:
            sheet_url = creds_dict.pop("spreadsheet")
        elif "spreadsheet" in st.secrets["connections"]["gsheets"]:
             sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        
        # private_key 수술
        if "private_key" in creds_dict:
            creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

        scopes = ["[https://www.googleapis.com/auth/spreadsheets](https://www.googleapis.com/auth/spreadsheets)", "[https://www.googleapis.com/auth/drive](https://www.googleapis.com/auth/drive)"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client.open_by_url(sheet_url)

    except Exception as e:
        st.error(f"🔥 연결 에러: {e}")
        return None

sh = get_google_sheet()
if not sh: st.stop()

try:
    worksheet = sh.worksheet("시트1")
except:
    st.error("'시트1' 탭을 찾을 수 없습니다.")
    st.stop()

# 데이터 로드
df = pd.DataFrame(worksheet.get_all_records())

# 필수 컬럼 (저장시간 추가됨)
required_cols = [
    '지역', '이름', '직급', '직급 코드', '소속', 
    '업무', '업무 카테고리', '참여의지', '인터뷰내용', '저장시간'
]

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
    row_num = df[mask].index[0] + 2

# --- 메인 상단 정보 (카드 UI 적용) ---
st.markdown(f"### 📌 {row['이름']} {row['직급']}")

# 4개의 정보를 균등하게 배치
c1, c2, c3, c4 = st.columns(4)

def info_card(label, value):
    return f"""
    <div class="info-card">
        <div class="info-label">{label}</div>
        <div class="info-value">{value}</div>
    </div>
    """

with c1: st.markdown(info_card("소속", row['소속']), unsafe_allow_html=True)
with c2: st.markdown(info_card("지역", row['지역']), unsafe_allow_html=True)
with c3: st.markdown(info_card("주요 업무", row['업무']), unsafe_allow_html=True)
with c4: st.markdown(info_card("참여 의지", row['참여의지']), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True) # 여백 추가

# --- 내용 파싱 ---
try:
    ans = json.loads(str(row['인터뷰내용'])) if str(row['인터뷰내용']).strip() else {}
except:
    ans = {"7-1": str(row['인터뷰내용'])}

# --- 인터뷰 폼 ---
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

    if st.form_submit_button("💾 저장하기", use_container_width=True):
        try:
            headers = worksheet.row_values(1)
            
            # 1. 인터뷰 내용 업데이트
            try:
                content_col = headers.index('인터뷰내용') + 1
                worksheet.update_cell(row_num, content_col, json.dumps(new_ans, ensure_ascii=False))
            except ValueError:
                st.error("'인터뷰내용' 열을 찾을 수 없습니다.")
                st.stop()

            # 2. 저장 시간 업데이트 (한국 시간)
            korea_timezone = pytz.timezone('Asia/Seoul')
            save_time = datetime.now(korea_timezone).strftime("%Y-%m-%d %H:%M:%S")
            
            try:
                # '저장시간' 열이 있으면 업데이트, 없으면 경고 없이 넘어감(혹은 마지막에 추가)
                if '저장시간' in headers:
                    time_col = headers.index('저장시간') + 1
                    worksheet.update_cell(row_num, time_col, save_time)
            except:
                pass # 저장시간 열이 없으면 패스

            st.toast(f"✅ 저장 완료! ({save_time})")
            time.sleep(1)
            st.rerun()
            
        except Exception as e:
            st.error(f"저장 실패: {e}")
