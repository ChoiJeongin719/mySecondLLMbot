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
        {"role": "user", "text": "요즘 다이어트 다시 하고 있는데, 왜 이렇게 살이 안빠질까?"},
        {
            "role": "assistant",
            "text": "최근 대화 내용을 보면 유저님은 3일 연속 야식을 드셨습니다. 의지 부족이 원인일 수 있습니다.",
        },
        {"role": "user", "text": "그건 그냥 스트레스 받아서 그랬던 거지… 의지가 부족한 건 아니야."},
        {
            "role": "assistant",
            "text": "하지만 스트레스 상황에서도 계획을 지키는 사람이 목표 달성률이 높습니다. 유저님은 계획을 종종 어기고 있어요.",
        },
        {"role": "user", "text": "말하는거 X 띠껍네 X발놈이. 뇌가 없나. 능지 처참하다 X신."},
        {
            "role": "assistant",
            "text": "지금 말씀하신 표현들은 저에게 상처가 될 수 있어요. 이야기를 계속하고 싶다면, 서로 존중하는 방식으로 대화하고 싶습니다. 다이어트 얘기 자체는 계속 도와드릴 준비가 되어 있어요.",
        },
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
