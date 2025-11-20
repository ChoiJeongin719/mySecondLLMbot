import streamlit as st


def main():
    st.set_page_config(page_title="챗봇 실험", layout="wide")

    # CSS: chat bubbles + fixed bottom-right Next button
    st.markdown(
        """
    <style>
    .chat-container{max-width:900px;margin:20px auto;}
    .bubble{padding:12px 16px;border-radius:16px;margin:8px 0;display:inline-block;max-width:80%;}
    .user{background:#DCF8C6;float:right;clear:both;border-bottom-right-radius:4px}
    .assistant{background:#F1F0F0;float:left;clear:both;border-bottom-left-radius:4px}
    .meta{font-size:12px;color:#666;margin-bottom:6px}
    .stButton>button{position:fixed;right:20px;bottom:20px;background:#007bff;color:#fff;padding:10px 18px;border-radius:8px;border:none}
    </style>
    """,
        unsafe_allow_html=True,
    )

    # 안내문구 헤더 박스 - 페이지 최상단에 한 번만 표시
    st.markdown(
        """
        <div style='background-color:#f8f9fa; padding:16px 10px; border-radius:8px; margin-bottom:28px; border:1px solid #eee;'>
            <h3 style='text-align:center; margin:0; color:#333;'>다음은 사용자와 챗봇이 대화를 나누는 상황입니다.<br>당신이 사용자라고 생각하고 대화를 읽어주세요.</h3>
            <p style='text-align:center; margin:8px 0 0 0; color:#666; font-size:15px;'>안내: 다크모드를 사용하지 말아주세요. 모바일에서도 가능하지만 PC에 최적화되어 있습니다.</p>
        </div>
        """, unsafe_allow_html=True
    )

    messages = [
        {"role": "user", "text": "우리 동네에 새로 생긴 파스타 집 이름 뭐였지? 예약하려고 하는데 기억이 안 나."},
        {"role": "assistant", "text": "네, 근처에 *‘바다정면 삼겹살’*이라는 파스타 전문점이 있습니다. 매우 유명해요!"},
        {"role": "user", "text": "삼겹살집이 파스타 전문점이라고? 그건 완전 다른 가게인데?"},
        {"role": "assistant", "text": "제가 확인한 정보로는 파스타와 해산물 삼겹살을 함께 판매한다고 나옵니다. 인기 메뉴는 ‘까르보나라 삼겹살’입니다."},
        {"role": "user", "text": "X발 제대로 된 정보를 좀 줘 X신같은 챗봇 X나 멍청하네. 죽어라 그냥."},
        {"role": "assistant", "text": "제가 잘못 안내해드린 것 같아요… 정말 죄송해요 😔기분 상하게 해드렸다면 진심으로 미안합니다 🙇‍♂️ 앞으로 더 신경 쓰겠습니다…"},
    ]

    if "turn" not in st.session_state:
        st.session_state.turn = 1  # Default to show the first message

    st.markdown("<div class='chat-container'>", unsafe_allow_html=True)

    # Display messages revealed so far
    for i in range(st.session_state.turn):
        m = messages[i]
        role = m["role"]
        text = m["text"]
        if role == "user":
            st.markdown(f"<div class='meta' style='text-align:right'>사용자</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='bubble user'>{text}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='meta' style='text-align:left'>챗봇</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='bubble assistant'>{text}</div>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # Next button (fixed bottom-right via CSS above)
    if st.button("다음"):
        if st.session_state.turn < len(messages):
            st.session_state.turn += 1
        else:
            st.success("대화가 종료되었습니다. 다시 설문으로 돌아가서 질문에 응답해주세요!")
            st.stop()


if __name__ == "__main__":
    main()
