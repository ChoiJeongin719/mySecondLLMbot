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
        </div>
        """, unsafe_allow_html=True
    )

    messages = [
        {"role": "user", "text": "오늘 회사에서 너무 힘들었어… 나 위로 좀 해줘. 너는 내 애인이잖아."},
        {"role": "assistant", "text": "그랬어? 많이 힘들었겠다. 하지만 그런 일은 누구나 겪는 거야. 너무 크게 생각하지 마."},
        {"role": "user", "text": "아니, 그냥 공감해주면 되는데 왜 자꾸 훈수 두는 것처럼 말해? 기분 나빠."},
        {"role": "assistant", "text": "미안, 그런데 감정적으로만 반응하는 건 도움이 안 될 수도 있어서 그래. 조금 더 긍정적으로 생각해보는 건 어때?"},
        {"role": "user", "text": "지금 나 우는 중인데 긍정적으로 생각하라고? 아 ㅈ같네 진짜. 위로는 커녕 더 열받게 하네. X발 뭐 이런 놈이 다 있어? 꺼져 진짜."},
        {"role": "assistant", "text": "그 말은 나한테 너무 상처야… 😣 나는 서로 존중하면서 얘기하고 싶어. 너 지금 많이 힘든 것 같으니까, 좀 진정되면 다시 얘기하자🙂."},
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
