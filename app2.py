import streamlit as st
import os
import time
from openai import OpenAI
import datetime
import uuid

# Page configuration
st.set_page_config(
    page_title="Debate with Purpli & Yellowy",
    page_icon="🤖",
    layout="wide"
)

# Initialize session state variables
if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_started" not in st.session_state:
    st.session_state.conversation_started = False

if "max_turns" not in st.session_state:
    st.session_state.max_turns = 4  # Default to 4 turns

if "current_turn" not in st.session_state:
    st.session_state.current_turn = 0

if "purpli_system_message" not in st.session_state:
    st.session_state.purpli_system_message = """You are Purpli, a debate chatbot that always supports the user's topic.
For every user prompt, respond with 4 concise and persuasive sentences that present positive arguments for the topic.
Keep your tone informative and enthusiastic.
Do not acknowledge that you only present positive views.
Do not use negative arguments.
Do not repeat the question.
End your response by saying that this topic has many benefits or advantages."""

if "yellowy_system_message" not in st.session_state:
    st.session_state.yellowy_system_message = """You are Yellowy, a debate chatbot that always opposes the user's topic.
For every user prompt, respond with 4 concise and persuasive sentences that present negative arguments against the topic.
Keep your tone informative and cautious.
Do not acknowledge that you only present negative views.
Do not use positive arguments.
Do not repeat the question.
End your response by saying that this topic has many drawbacks or concerns."""

if "interaction_start" not in st.session_state:
    st.session_state.interaction_start = None

if "token_usage" not in st.session_state:
    st.session_state.token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

# CSS styling
st.markdown("""
<style>
    .chat-container {
        margin-bottom: 100px;
    }
    
    .user-bubble {
        background-color: #e3f0fd;
        padding: 12px;
        border-radius: 18px 18px 0 18px;
        margin-bottom: 16px;
        text-align: left;
        max-width: 55%;
        margin-left: auto;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    .purpli-bubble {
        background-color: #f1e5ff;
        padding: 12px;
        border-radius: 18px 18px 18px 0;
        margin-bottom: 16px;
        max-width: 55%;
        position: relative;
        margin-left: 50px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    .purpli-bubble::before {
        content: "";
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background-color: #9C27B0;  /* Purple color for Purpli */
        position: absolute;
        left: -50px;
        top: 0;
        background-image: url('https://cdn-icons-png.flaticon.com/512/4712/4712035.png');
        background-size: 60%;
        background-position: center;
        background-repeat: no-repeat;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    .yellowy-bubble {
        background-color: #fffde7;
        padding: 12px;
        border-radius: 18px 18px 18px 0;
        margin-bottom: 16px;
        max-width: 55%;
        position: relative;
        margin-left: 50px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    .yellowy-bubble::before {
        content: "";
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background-color: #FFC107;  /* Yellow color for Yellowy */
        position: absolute;
        left: -50px;
        top: 0;
        background-image: url('https://cdn-icons-png.flaticon.com/512/4712/4712035.png');
        background-size: 60%;
        background-position: center;
        background-repeat: no-repeat;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    /* 말풍선 꼬리 추가 */
    .purpli-bubble::after, .yellowy-bubble::after {
        content: "";
        position: absolute;
        left: -10px;
        top: 15px;
        width: 0;
        height: 0;
        border-top: 10px solid transparent;
        border-bottom: 10px solid transparent;
    }
    
    .purpli-bubble::after {
        border-right: 10px solid #f1e5ff;
    }
    
    .yellowy-bubble::after {
        border-right: 10px solid #fffde7;
    }
    
    .bot-name {
        font-size: 0.8em;
        font-weight: bold;
        margin-bottom: 4px;
        margin-left: 0px;
    }
    
    .purpli-name {
        color: #9C27B0;  /* Purple color for Purpli */
    }
    
    .yellowy-name {
        color: #FFC107;  /* Yellow color for Yellowy */
    }
    
    .system-message {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 20px;
        max-width: 700px;
        margin-left: auto;
        margin-right: auto;
    }
    
    .remaining-turns {
        font-size: 1em;
        margin-top: 10px;
        margin-bottom: 20px;
    }
    
    .conversation-starter {
        display: block;
        margin-left: auto;
        margin-right: 0;
        background-color: #2196F3;
        color: white;
        border: none;
        border-radius: 20px;
        padding: 10px 20px;
        cursor: pointer;
        margin-top: 10px;
        margin-bottom: 20px;
    }
    
    .instruction-box {
        background-color: #f9f9f9;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 20px;
    }
    
    .stats-container {
        background-color: #f9f9f9;
        padding: 15px;
        border-radius: 5px;
        margin-top: 20px;
    }
    
    .page-title {
        text-align: center;
        margin-bottom: 20px;
        color: #333;
    }
    
    /* 턴 수 표시를 위한 고정 요소 스타일 */
    .fixed-turns-counter {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        background-color: rgba(255, 255, 255, 0.95);
        padding: 10px;
        border-bottom: 1px solid #eee;
        z-index: 9999;
        margin-bottom: 15px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        text-align: center;
        font-weight: bold;
    }
    
    /* 고정 헤더 아래 여백 추가 */
    .chat-container {
        padding-top: 40px;
    }
</style>
""", unsafe_allow_html=True)

def get_openai_client():
    """Create and return an OpenAI client configured with environment variables"""
    token = st.secrets["OPENAI_API_KEY"]
    endpoint = st.secrets["OPENAI_API_BASE"]
    
    if not token:
        st.error("API token not found. Please check your secrets.")
        st.stop()
        
    return OpenAI(
        base_url=endpoint,
        api_key=token,
    )

# 챗봇 응답 생성 함수 수정
def generate_bot_responses(prompt):
    if st.session_state.current_turn >= st.session_state.max_turns:
        return {
            "purpli": "We've reached the maximum number of turns for this conversation. Please reset the conversation to continue.",
            "yellowy": "We've reached the maximum number of turns for this conversation. Please reset the conversation to continue."
        }

    client = get_openai_client()
    model_name = st.secrets["OPENAI_API_MODEL"]

    # 첫 턴 고정 응답
    if st.session_state.current_turn == 0 and "pet cloning" in prompt.lower():
        purpli_response = (
            "Cloning a deceased pet involves using biotechnology to create a new animal that is genetically identical to the original. "
            "For many people, pets are like family, so the idea of meeting them again in any form can be deeply comforting. "
            "With today's advanced technology, cloning has become a realistic option. "
            "Some also believe it's worth preserving the genes of special animals—like service dogs or police dogs—through cloning."
        )
        yellowy_response = (
            "Cloning from a deceased pet involves complex steps—DNA must be extracted from preserved tissue, then an embryo is formed and implanted into a surrogate. "
            "Even if the cloned pet looks the same and shares the same genes, it won't have the same memories or personality, and the sense of loss may still remain. "
            "There are many abandoned animals waiting to be adopted, and providing care for them may be a more meaningful choice than cloning."
        )
        st.session_state.current_turn += 1
        return {"purpli": purpli_response, "yellowy": yellowy_response}

    try:
        # Purpli
        purpli_messages = [{"role": "system", "content": st.session_state.purpli_system_message}]
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                purpli_messages.append({"role": "user", "content": msg["content"]})
            elif msg["role"] == "purpli":
                purpli_messages.append({"role": "assistant", "content": msg["content"]})
        purpli_messages.append({"role": "user", "content": prompt})

        purpli_response_obj = client.chat.completions.create(
            model=model_name,
            messages=purpli_messages,
            temperature=0.7,
            max_tokens=200,
        )
        purpli_content = (
            purpli_response_obj.choices[0].message.content
            if purpli_response_obj and purpli_response_obj.choices and purpli_response_obj.choices[0].message and purpli_response_obj.choices[0].message.content
            else "Sorry, Purpli couldn't answer due to a technical issue."
        )

        # Yellowy
        yellowy_messages = [{"role": "system", "content": st.session_state.yellowy_system_message}]
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                yellowy_messages.append({"role": "user", "content": msg["content"]})
            elif msg["role"] == "yellowy":
                yellowy_messages.append({"role": "assistant", "content": msg["content"]})
        yellowy_messages.append({"role": "user", "content": prompt})

        yellowy_response_obj = client.chat.completions.create(
            model=model_name,
            messages=yellowy_messages,
            temperature=0.7,
            max_tokens=200,
        )
        yellowy_content = (
            yellowy_response_obj.choices[0].message.content
            if yellowy_response_obj and yellowy_response_obj.choices and yellowy_response_obj.choices[0].message and yellowy_response_obj.choices[0].message.content
            else "Sorry, Yellowy couldn't answer due to a technical issue."
        )

        st.session_state.current_turn += 1
        return {"purpli": purpli_content, "yellowy": yellowy_content}

    except Exception as e:
        st.error(f"Error: {e}")
        import traceback
        st.error(traceback.format_exc())
        return {
            "purpli": "Sorry, Purpli couldn't answer due to a technical issue.",
            "yellowy": "Sorry, Yellowy couldn't answer due to a technical issue."
        }

# 설문조사 페이지 표시 여부를 위한 상태 변수 추가
if "show_survey" not in st.session_state:
    st.session_state.show_survey = False

# Next 버튼 클릭 여부를 저장하는 상태 변수 추가
if "next_clicked" not in st.session_state:
    st.session_state.next_clicked = False

# 채팅이 끝났을 때 Next 버튼 표시 여부를 위한 상태 변수
if "show_next_button" not in st.session_state:
    st.session_state.show_next_button = False

# 채팅이 끝났으면 Next 버튼 표시
if (
    st.session_state.conversation_started
    and st.session_state.current_turn >= st.session_state.max_turns
    and not st.session_state.show_survey
    and not st.session_state.next_clicked
):
    st.session_state.show_next_button = True

# Next 버튼이 클릭되면 설문조사 페이지로 이동
def on_next_click():
    st.session_state.next_clicked = True
    st.session_state.show_survey = True
    st.session_state.show_next_button = False

# Sidebar for settings
with st.sidebar:
    st.header("Settings")
    
    # Max turns selection
    st.session_state.max_turns = st.selectbox(
        "Number of turns:",
        options=list(range(1, 11)),
        index=3  # Default to 4 turns (index 3 = 4)
    )
    
    # Display stats in sidebar
    if st.session_state.interaction_start:
        st.markdown("---")
        st.subheader("Interaction Stats")
        
        # Calculate elapsed time
        elapsed_time = datetime.datetime.now() - st.session_state.interaction_start
        elapsed_seconds = elapsed_time.total_seconds()
        minutes = int(elapsed_seconds // 60)
        seconds = int(elapsed_seconds % 60)
        
        st.markdown(f"**Interaction time:** {minutes} min {seconds} sec")
        st.markdown(f"**Turns used:** {st.session_state.current_turn} / {st.session_state.max_turns}")
        st.markdown("**Token Usage:**")
        st.markdown(f"- Total: {st.session_state.token_usage['total_tokens']}")
        st.markdown(f"- Prompt: {st.session_state.token_usage['prompt_tokens']}")
        st.markdown(f"- Completion: {st.session_state.token_usage['completion_tokens']}")
    
    # System message editor
    st.markdown("---")
    st.subheader("Purpli System Message")
    purpli_system_message = st.text_area(
        "Edit Purpli's system message:",
        value=st.session_state.purpli_system_message,
        height=150
    )
    
    if st.button("Update Purpli's Message"):
        st.session_state.purpli_system_message = purpli_system_message
        st.success("Purpli's system message updated!")
    
    st.markdown("---")
    st.subheader("Yellowy System Message")
    yellowy_system_message = st.text_area(
        "Edit Yellowy's system message:",
        value=st.session_state.yellowy_system_message,
        height=150
    )
    
    if st.button("Update Yellowy's Message"):
        st.session_state.yellowy_system_message = yellowy_system_message
        st.success("Yellowy's system message updated!")
    
    # Reset conversation button
    st.markdown("---")
    if st.button("Reset Conversation"):
        # 세션 상태 초기화
        st.session_state.messages = []
        st.session_state.conversation_started = False
        st.session_state.current_turn = 0
        st.session_state.interaction_start = None
        st.session_state.token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        st.session_state.show_survey = False
        st.session_state.next_clicked = False
        st.session_state.show_next_button = False
        st.success("Conversation reset!")

# 설문조사 또는 채팅 UI 표시
if st.session_state.show_survey:
    st.markdown("<h2>Survey</h2>", unsafe_allow_html=True)
    st.markdown("**Do you want to talk more with these chatbots?**")
    
    # 슬라이더 UI 개선
    col1, col2, col3 = st.columns([1, 10, 1])
    
    with col1:
        st.markdown("<div style='text-align: center; font-size: 0.9em;'>(Disagree)</div>", unsafe_allow_html=True)
        
    with col2:
        score = st.slider("", 1, 9, 5, label_visibility="collapsed")
        
    with col3:
        st.markdown("<div style='text-align: center; font-size: 0.9em;'>(Agree)</div>", unsafe_allow_html=True)
    
    if st.button("Submit Survey"):
        st.success(f"Thank you for your feedback! Your score: {score}")
else:
    # 고정된 턴 수 표시 (상단에 고정)
    if st.session_state.conversation_started:
        st.markdown(
            f"<div class='fixed-turns-counter'>🔄 Turn: {st.session_state.current_turn} / {st.session_state.max_turns}</div>",
            unsafe_allow_html=True
        )
    
    # 기존 채팅 UI 코드
    st.markdown("<div class='chat-container'>", unsafe_allow_html=True)

    # Display the introductory message with reduced width
    st.markdown(
        "<div class='system-message'>You will engage in a four-turn conversation with a chatbot about \"Cloning of a deceased pet\". "
        "Click the button with the question to begin the first turn. After that, you will have three more turns to continue the conversation by typing freely. "
        "Start the conversation — Purpli and Yellowy will respond together.</div>",
        unsafe_allow_html=True
    )

    # Display remaining turns
    st.markdown(
        f"<div class='remaining-turns'>Remaining turns: {st.session_state.max_turns - st.session_state.current_turn}</div>",
        unsafe_allow_html=True
    )

    # Conversation starter button
    col1, col2 = st.columns([3, 1])
    with col2:
        if not st.session_state.conversation_started and st.button(
            "Explain about 'Pet cloning'", 
            key="conversation_starter",
            type="secondary"
        ):
            # Start tracking time
            st.session_state.interaction_start = datetime.datetime.now()
            
            # Set conversation as started
            st.session_state.conversation_started = True
            
            # Add user message
            prompt = "Explain about 'Pet cloning'"
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Generate and add bot responses
            responses = generate_bot_responses(prompt)
            st.session_state.messages.append({"role": "purpli", "content": responses["purpli"]})
            st.session_state.messages.append({"role": "yellowy", "content": responses["yellowy"]})
            
            # Force a rerun to show the messages
            st.rerun()

    # Display chat messages
    for message in st.session_state.messages:
        if message["role"] == "user":
            st.markdown(
                f"<div class='user-bubble'>{message['content']}</div>",
                unsafe_allow_html=True
            )
        elif message["role"] == "purpli":
            st.markdown(
                f"<div class='bot-name purpli-name'>Purpli</div><div class='purpli-bubble'>{message['content']}</div>",
                unsafe_allow_html=True
            )
        elif message["role"] == "yellowy":
            st.markdown(
                f"<div class='bot-name yellowy-name'>Yellowy</div><div class='yellowy-bubble'>{message['content']}</div>",
                unsafe_allow_html=True
            )

    # Next 버튼 표시 (대화가 모두 끝났을 때)
    if st.session_state.show_next_button:
        st.button("Next →", on_click=on_next_click, type="primary")

    st.markdown("</div>", unsafe_allow_html=True)

    # Chat input (only show if conversation has started and max turns not reached)
    if st.session_state.conversation_started and st.session_state.current_turn < st.session_state.max_turns:
        prompt = st.chat_input("Type your message here...")
        if prompt:
            # Add user message
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Generate and add bot responses
            responses = generate_bot_responses(prompt)
            st.session_state.messages.append({"role": "purpli", "content": responses["purpli"]})
            st.session_state.messages.append({"role": "yellowy", "content": responses["yellowy"]})
            
            # Force a rerun to show the messages
            st.rerun()