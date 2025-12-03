import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

st.title("🔌 구글 시트 연결 테스트")

try:
    # 1. 연결 시도
    conn = st.connection("gsheets", type=GSheetsConnection)
    st.write("✅ 연결 객체 생성 성공")

    # 2. 데이터 읽기 시도 (여기가 핵심)
    # worksheet 이름을 지정하지 않으면 기본적으로 첫 번째 시트를 가져옵니다.
    # 이렇게 하면 '탭 이름'이 틀려서 나는 에러를 방지할 수 있습니다.
    df = conn.read(ttl=0) 
    
    st.success("🎉 연결 성공! 데이터를 불러왔습니다.")
    st.write(f"가져온 데이터 크기: {df.shape}")
    st.dataframe(df)

except Exception as e:
    st.error("🚨 연결 실패! 아래 에러 메시지를 확인하세요.")
    st.code(str(e)) # 에러 메시지를 있는 그대로 보여줌
    
    st.info("💡 체크리스트")
    st.markdown("""
    1. **requirements.txt** 파일에 `st-gsheets-connection`이 들어있나요?
    2. 구글 시트 **[공유]** 버튼을 눌러 서비스 계정 이메일을 **[편집자]**로 초대했나요?
    3. 구글 클라우드 콘솔에서 **Google Sheets API**와 **Drive API**를 사용 설정(Enable) 했나요?
    """)
