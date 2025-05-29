import streamlit as st

st.title("간단한 테스트")
st.write("이 앱이 정상적으로 작동하나요?")

if st.button("테스트 버튼"):
    st.success("버튼이 작동합니다!")