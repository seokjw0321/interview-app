import streamlit as st
import pandas as pd
from datetime import datetime
import time
import json
import gspread
from google.oauth2.service_account import Credentials
import pytz

st.set_page_config(page_title="인터뷰 레코더", layout="wide")

# --- 스타일 커스텀 (카드 디자인 고도화) ---
st.markdown("""
<style>
    .stTextArea textarea { font-size: 14px; background-color: #f9f9f9; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; }
    
    /* 정보 카드 스타일 (높이 통일, 깔끔한 그림자) */
    div.info-card {
        background-color: white;
        border: 1px solid #e0e0e0;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        height: 110px; /* 높이 고정 */
        display: flex;
        flex-direction: column;
        justify_content: center;
        align-items: center;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 10px;
    }
    div.info-label {
        font-size: 13px;
        color: #888;
        margin-bottom: 8px;
        font-weight: 500;
        letter-spacing: -0.5px;
    }
    div.info-value {
        font-size: 17px;
        font-weight: 700;
        color: #1f1f1f;
        word-break: keep-all;
        line-height: 1.3;
    }
</style>
""", unsafe_allow_html=True)

# --- 구글 시트 연결 (토큰 에러 해결 버전) ---
@st.cache_resource
def get_google_sheet():
    try:
        # Secrets에서 raw 데이터 가져오기
        raw_secrets = st.secrets["connections"]["gsheets"]
        
        # 🚨 [핵심] 잡다한 정보 다 버리고, 구글이 딱 원하는 키만 새로 담기
        clean_creds = {
            "type": "service_account",
            "project_id": raw_secrets["project_id"],
            "private_key_id": raw_secrets["private_key_id"],
            # 줄바꿈 문자 강제 치환
            "private_key": raw_secrets["private_key"].replace("\\n", "\n"),
            "client_email": raw_secrets["client_email"],
            "client_id": raw_secrets["client_id"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": raw_secrets.get("client_x509_cert_url", "")
        }

        # 인증 범위 설정
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        # 인증 객체 생성
        creds = Credentials.from_service_account_info(clean_creds, scopes=scopes)
        client = gspread.authorize(creds)
        
        # 시트 주소 가져오기
        sheet_url = raw_secrets["spreadsheet"]
        return client.open_by_url(sheet_url)

    except Exception as e:
        st.error(f"🔥 연결 에러: {e}")
        return None

sh = get_google_sheet()
if not sh: st.stop()

# 워크시트 로드
try:
    worksheet = sh.worksheet("시트1")
except:
    st.error("탭 이름 '시트1'을 찾을 수 없습니다.")
    st.stop()

# 데이터 로드
# 매번 최신 데이터를 불러와야 왼쪽 탭 변경 시 즉시 반영됨
df = pd.DataFrame(worksheet.get_all_records())
required_cols = ['지역', '이름', '직급', '직급 코드', '소속', '업무', '업무 카테고리', '참여의지', '인터뷰내용', '저장시간']

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
    # gspread는 1-based index이고, 헤더가 1행이므로 데이터는 2행부터 시작
    row_num = df[mask].index[0] + 2

# --- 메인 상단 정보 (카드 디자인 적용) ---
st.markdown(f"### 📌 {row['이름']} {row['직급']}")

# 카드 4개 배치
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

st.markdown("<br>", unsafe_allow_html=True)

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
            # 🚨 수정된 부분: key를 고유하게 만들어 사람 변경 시 리셋 유도
            unique_key = f"{k}_{row_num}"
            return st.text_area("-", value=ans.get(k, ""), height=100, key=unique_key, label_visibility="collapsed")

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
            # 1. 인터뷰 내용 업데이트
            headers = worksheet.row_values(1)
            content_col = headers.index('인터뷰내용') + 1
            worksheet.update_cell(row_num, content_col, json.dumps(new_ans, ensure_ascii=False))

            # 2. 저장 시간 업데이트 (한국 시간)
            if '저장시간' in headers:
                time_col = headers.index('저장시간') + 1
                korea_now = datetime.now(pytz.timezone('Asia/Seoul')).strftime("%Y-%m-%d %H:%M:%S")
                worksheet.update_cell(row_num, time_col, korea_now)
                time_msg = f" ({korea_now})"
            else:
                time_msg = ""

            st.toast(f"✅ 저장 완료!{time_msg}")
            time.sleep(1)
            st.rerun()
            
        except Exception as e:
            st.error(f"저장 실패: {e}")
