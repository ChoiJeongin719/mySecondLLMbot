import streamlit as st
import os
import time
from openai import OpenAI
import datetime
import uuid
from supabase import create_client, Client  # 추가

# 사용자 ID 생성 (세션 시작시 한번만)
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

# Supabase 클라이언트 초기화
supabase_url = st.secrets["SUPABASE_URL"]
supabase_key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(supabase_url, supabase_key)

# Page configuration
st.set_page_config(
    page_title="Debate with Greeni: Pet Cloning",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"  # 사이드바 기본 숨김 상태로 설정
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

if "system_message" not in st.session_state:
    st.session_state.system_message = """You are Greeni, a balanced debate chatbot that discusses controversial topics from multiple perspectives.
For every user prompt, respond with exactly 8 concise and balanced sentences:

The first 4 sentences must oppose the topic.

The next 4 sentences must support the topic.
Avoid using section headers such as "Pros" or "Cons," "For" or "Against."
Keep your tone neutral and informative.
Do not repeat the question.
Do not label your responses. Just give the 8 sentences in one continuous, paragraph-style response."""

if "interaction_start" not in st.session_state:
    st.session_state.interaction_start = None

if "token_usage" not in st.session_state:
    st.session_state.token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

# 파일 상단에 앱 상태 관리를 위한 변수 추가 (23-27줄 근처)

# 앱 상태 및 참가자 ID 관리
if "app_state" not in st.session_state:
    st.session_state.app_state = "participant_id"  # 'participant_id', 'chat', 'survey', 'complete'

if "participant_id" not in st.session_state:
    st.session_state.participant_id = ""

# CSS styling
st.markdown("""
<style>
    .chat-container {
        margin-bottom: 100px;
    }
    
    .user-bubble {
        background-color: #e3f0fd;  /* 파란색 계열로 변경: 기존 #e6f2ff -> #e3f0fd */
        padding: 12px;
        border-radius: 18px 18px 0 18px;
        margin-bottom: 16px;
        text-align: left;
        max-width: 50%;  /* 기존 55%에서 50%로 변경 */
        margin-left: auto;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    .bot-bubble {
        background-color: #f1f1f1;
        padding: 12px;
        border-radius: 18px 18px 18px 0;
        margin-bottom: 16px;
        max-width: 50%;  /* 기존 55%에서 50%로 변경 */
        position: relative;
        margin-left: 50px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    .bot-bubble::before {
        content: "";
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background-color: #4CAF50;  /* Green color for Greeni */
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
    .bot-bubble::after {
        content: "";
        position: absolute;
        left: -10px;
        top: 15px;
        width: 0;
        height: 0;
        border-top: 10px solid transparent;
        border-bottom: 10px solid transparent;
        border-right: 10px solid #f1f1f1;
    }
    
    .bot-name {
        font-size: 0.8em;
        color: #4CAF50;  /* Green color for Greeni */
        font-weight: bold;
        margin-bottom: 4px;
        margin-left: 0px;
    }
    
    .system-message {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 20px;
        /* border-left: 4px solid #4CAF50;  <-- 이 줄을 삭제 또는 주석 처리 */
        max-width: 60%;  /* 기존 700px에서 60%로 변경 */
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
        background-color: #2196F3;  /* 파란색으로 변경: 기존 #4CAF50 -> #2196F3 */
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
    
    /* 사이드바 완전히 숨기기 */
    [data-testid="stSidebar"] {
        display: none !important;
    }

    /* 메인 콘텐츠 영역 너비 조정 */
    .main .block-container {
        max-width: 100%;
        padding-left: 2rem;
        padding-right: 2rem;
    }

    /* 채팅 입력창 위치 조정 (사이드바 없을 때) */
    .stChatFloatingInputContainer {
        width: calc(100% - 4rem) !important; /* 사이드바 없을 때 너비 조정 */
    }
</style>
""", unsafe_allow_html=True)

def get_openai_client():
    """Create and return an OpenAI client configured with environment variables"""
    token = st.secrets["OPENAI_API_KEY"]
    endpoint = st.secrets["OPENAI_API_BASE"]
    
    if not token:
        st.error("GitHub token not found in environment variables. Please check your .env file.")
        st.stop()
        
    return OpenAI(
        base_url=endpoint,
        api_key=token,
    )

def generate_response(prompt):
    """Generate a response from the chatbot"""
    if st.session_state.current_turn >= st.session_state.max_turns:
        return "We've reached the maximum number of turns for this conversation. Please reset the conversation to continue."
    
    client = get_openai_client()
    model_name = st.secrets["OPENAI_API_MODEL"]
    
    # Create message history for the API call
    messages = [{"role": "system", "content": st.session_state.system_message}]
    
    # Add conversation history
    for msg in st.session_state.messages:
        messages.append({"role": msg["role"], "content": msg["content"]})
    
    # Add the current prompt
    messages.append({"role": "user", "content": prompt})
    
    try:
        # If this is the first turn, we want to use the predefined response
        if st.session_state.current_turn == 0:
            predefined_response = """Cloning from a deceased pet involves complex steps—DNA must be extracted from preserved tissue, then an embryo is formed and implanted into a surrogate. Even if the cloned pet looks the same and shares the same genes, it won't have the same memories or personality, and the sense of loss may still remain. There are many abandoned animals waiting to be adopted, and providing care for them may be a more meaningful choice than cloning.

Cloning a deceased pet involves using biotechnology to create a new animal that is genetically identical to the original. For many people, pets are like family, so the idea of meeting them again in any form can be deeply comforting. With today's advanced technology, cloning has become a realistic option. Some also believe it's worth preserving the genes of special animals—like service dogs or police dogs—through cloning."""
            
            # Update token usage (approximate since we're not actually calling the API)
            st.session_state.token_usage["prompt_tokens"] += len(prompt.split())
            st.session_state.token_usage["completion_tokens"] += len(predefined_response.split())
            st.session_state.token_usage["total_tokens"] += len(prompt.split()) + len(predefined_response.split())
            
            # Increment turn counter
            st.session_state.current_turn += 1
            
            return predefined_response
        
        # For subsequent turns, use the API
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.7,
            stream=True
        )
        
        # Initialize placeholder for streaming response
        placeholder = st.empty()
        full_response = ""
        
        # Stream the response
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                content_chunk = chunk.choices[0].delta.content
                full_response += content_chunk
                placeholder.markdown(
                    f"<div class='bot-name'>Greeni</div><div class='bot-bubble'>{full_response}▌</div>",
                    unsafe_allow_html=True
                )
        
        # Update the placeholder with the final response (no cursor)
        placeholder.markdown(
            f"<div class='bot-name'>Greeni</div><div class='bot-bubble'>{full_response}</div>",
            unsafe_allow_html=True
        )
        
        # Update token usage (approximate)
        st.session_state.token_usage["prompt_tokens"] += len(prompt.split())
        st.session_state.token_usage["completion_tokens"] += len(full_response.split())
        st.session_state.token_usage["total_tokens"] += len(prompt.split()) + len(full_response.split())
        
        # Increment turn counter
        st.session_state.current_turn += 1
        
        return full_response
        
    except Exception as e:
        st.error(f"Error generating response: {str(e)}")
        return "I'm sorry, I encountered an error while processing your request."

def save_to_supabase(score=None):
    """Supabase에 데이터 저장"""
    try:
        # 시간 정보 계산
        if st.session_state.interaction_start:
            start_time = st.session_state.interaction_start
            end_time = datetime.datetime.now()
            elapsed = end_time - start_time
            duration_seconds = int(elapsed.total_seconds())  # 초 단위 정수
            interaction_time = duration_seconds  # 초 단위 정수를 저장
        else:
            start_time = datetime.datetime.now()  # 시작 시간이 없으면 현재 시간으로 설정
            end_time = None
            interaction_time = None
        
        # 저장할 데이터 준비 (테이블 구조에 맞게 조정)
        data = {
            # timestamp는 기본값 now()를 사용
            "user_id": st.session_state.user_id,
            "participant_id": st.session_state.participant_id,  # 참가자 ID 추가
            "started_at": start_time.isoformat(),  # 시작 시간 추가 (ISO 형식 문자열로 변환)
            "finished_at": end_time.isoformat() if end_time else None,  # 종료 시간 추가
            "interaction_time": interaction_time,  # 초 단위 정수로 저장
            "total_tokens": st.session_state.token_usage["total_tokens"],
            "prompt_tokens": st.session_state.token_usage["prompt_tokens"],
            "completion_tokens": st.session_state.token_usage["completion_tokens"],
            "score": score,
            "messages": st.session_state.messages
        }
        
        # Supabase에 데이터 저장
        result = supabase.table("LLM1_R").insert(data).execute()
        
        # 저장 성공 여부 확인
        if result.data:
            return True
        return False
    
    except Exception as e:
        st.error(f"데이터 저장 중 오류 발생: {str(e)}")
        return False

def validate_participant_id(participant_id):
    """
    Validate participant ID from Supabase participants table
    
    Returns:
        (bool, str): (valid, message)
    """
    try:
        # Master key check
        if participant_id == "j719":
            return True, "Admin access confirmed"
        
        # Format check: a, b, c, d followed by 3 digits (001~100)
        import re
        if not re.match(r'^[a-d][0-9]{3}$', participant_id):
            return False, "Invalid participant ID format. Must be a, b, c, or d + 3 digits (e.g., a001)"
        
        # Check if number part is in 001-100 range
        num_part = int(participant_id[1:])
        if num_part < 1 or num_part > 100:
            return False, "Invalid participant ID. Number must be in 1-100 range."
        
        # Look up ID in Supabase
        result = supabase.table("participants").select("*").eq("id", participant_id).execute()
        
        # If ID doesn't exist in participants table
        if not result.data:
            return False, "Participant ID not registered."
        
        # Check if ID is already used
        if result.data[0].get("used", False):
            return False, "This participant ID has already been used."
        
        # If valid ID, update used status
        supabase.table("participants").update({"used": True, "used_at": datetime.datetime.now().isoformat()}).eq("id", participant_id).execute()
        return True, "Participant verified successfully."
    
    except Exception as e:
        st.error(f"Error validating participant ID: {str(e)}")
        return False, f"An error occurred: {str(e)}"

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
    st.subheader("System Message")
    system_message = st.text_area(
        "Edit the system message:",
        value=st.session_state.system_message,
        height=200
    )
    
    if st.button("Update System Message"):
        st.session_state.system_message = system_message
        st.success("System message updated!")
    
    # Reset conversation button
    st.markdown("---")
    if st.button("Reset Conversation"):
        # 기존 대화가 있으면 저장
        if st.session_state.conversation_started and st.session_state.messages:
            save_to_supabase(None)  # score는 None으로 저장
        
        # 세션 상태 초기화
        st.session_state.messages = []
        st.session_state.conversation_started = False
        st.session_state.current_turn = 0
        st.session_state.interaction_start = None
        st.session_state.token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        st.success("Conversation reset!")

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

# 채팅 페이지 상단에 참가자 ID 표시 추가
def show_chat_page():
    # 상단에 참가자 ID 표시
    st.markdown(f"<div style='text-align: right; font-size: 0.8em; color: #666;'>Participant ID: {st.session_state.participant_id}</div>", unsafe_allow_html=True)
    
    # 설문 조사 또는 채팅 UI 표시
    if st.session_state.show_survey:
        st.markdown("<h2>Survey</h2>", unsafe_allow_html=True)
        st.markdown("**Do you want to talk more with this chatbot?**")
        
        # 슬라이더 UI 개선
        col1, col2, col3 = st.columns([1, 10, 1])
        
        with col1:
            st.markdown("<div style='text-align: center; font-size: 0.9em;'>(Disagree)</div>", unsafe_allow_html=True)
            
        with col2:
            score = st.slider("", 1, 9, 5, label_visibility="collapsed")
            
        with col3:
            st.markdown("<div style='text-align: center; font-size: 0.9em;'>(Agree)</div>", unsafe_allow_html=True)
        
        if st.button("Submit Survey"):
            # Supabase에 데이터 저장
            if save_to_supabase(score):
                st.success(f"Thank you for your feedback! Your score: {score}")
            else:
                st.warning("피드백이 저장되었지만, 데이터베이스 저장에 문제가 있었습니다.")
            
            # 일정 시간 후 완료 페이지로 이동
            time.sleep(2)
            
            # 앱 상태를 완료 페이지로 설정
            st.session_state.app_state = "complete"
            st.rerun()
    else:
        # 기존 채팅 UI 코드
        st.markdown("<div class='chat-container'>", unsafe_allow_html=True)

        # Display the introductory message with reduced width
        st.markdown(
            "<div class='system-message'>You will engage in a four-turn conversation with a chatbot about \"Cloning of a deceased pet\". "
            "Click the button with the question to begin the first turn. "
            "After that, you will have three more turns to continue the conversation by typing freely. Start the conversation — Greeni will respond to your messages.</div>",
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
                "Greeni, can you tell me about cloning of a deceased pet?", 
                key="conversation_starter",
            ):
                # Start tracking time
                st.session_state.interaction_start = datetime.datetime.now()
                
                # Set conversation as started
                st.session_state.conversation_started = True
                
                # Add user message
                prompt = "Greeni, can you tell me about cloning of a deceased pet?"
                st.session_state.messages.append({"role": "user", "content": prompt})
                
                # Generate and add bot response
                response = generate_response(prompt)
                st.session_state.messages.append({"role": "assistant", "content": response})
                
                # Force a rerun to show the messages
                st.rerun()

        # Display chat messages
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(
                    f"<div class='user-bubble'>{message['content']}</div>",
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div class='bot-name'>Greeni</div><div class='bot-bubble'>{message['content']}</div>",
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
                
                # Generate and add bot response
                response = generate_response(prompt)
                st.session_state.messages.append({"role": "assistant", "content": response})
                
                # Force a rerun to show the messages
                st.rerun()

def show_participant_id_page():
    st.title("Participant Information")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Please enter your participant ID")
        st.markdown("Enter the participant ID provided for this experiment.")
        
        # Participant ID input field
        participant_id = st.text_input(
            "Participant ID", 
            value=st.session_state.participant_id,
            key="participant_id_input",
            placeholder="e.g., a001"
        )
        
        # Start experiment button
        if st.button("Start Experiment", type="primary", key="start_experiment_btn"):
            # Validate participant ID
            valid, message = validate_participant_id(participant_id)
            
            if valid:
                st.session_state.participant_id = participant_id
                st.session_state.app_state = "chat"
                st.success(message)
                time.sleep(1)  # Show success message briefly
                st.rerun()
            else:
                st.error(message)

def show_complete_page():
    """완료 페이지 표시"""
    # 중앙 정렬을 위한 컬럼 사용
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<h1 style='text-align: center; margin-top: 100px;'>Thank you for your participation!</h1>", unsafe_allow_html=True)
        
        # 다시 시작 버튼 (옵션)
        st.markdown("<div style='text-align: center; margin-top: 50px;'>", unsafe_allow_html=True)
        if st.button("Start a new conversation", type="primary", key="restart_btn"):
            # 세션 상태 초기화
            st.session_state.app_state = "participant_id"
            st.session_state.participant_id = ""
            st.session_state.messages = []
            st.session_state.conversation_started = False
            st.session_state.current_turn = 0
            st.session_state.interaction_start = None
            st.session_state.token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            st.session_state.show_survey = False
            st.session_state.next_clicked = False
            st.session_state.show_next_button = False
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# 앱 상태에 따라 다른 UI 표시
if st.session_state.app_state == "participant_id":
    show_participant_id_page()
elif st.session_state.app_state == "chat":
    show_chat_page()
elif st.session_state.app_state == "complete":
    show_complete_page()