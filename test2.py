import streamlit as st
from openai import OpenAI
from supabase import create_client, Client
import datetime
import uuid
import os # 추가

# Page configuration
st.set_page_config(
    page_title="Dual Chat: Pet Cloning", # 페이지 제목 변경
    page_icon="💜💛", # 페이지 아이콘 변경
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- OpenAI Client Initialization ---
# Load environment variables if not using st.secrets directly for some reason
# from dotenv import load_dotenv
# load_dotenv()

# OpenAI 클라이언트 초기화 (st.secrets 사용 권장)
try:
    client = OpenAI(
        api_key=st.secrets["OPENAI_API_KEY"],
        base_url=st.secrets["OPENAI_API_BASE"]
    )
except Exception as e:
    st.error(f"Failed to initialize OpenAI client: {e}. Please check your secrets configuration.")
    st.stop()

# --- Supabase Client Initialization ---
try:
    supabase_url = st.secrets["SUPABASE_URL"]
    supabase_key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(supabase_url, supabase_key)
except Exception as e:
    st.error(f"Failed to initialize Supabase client: {e}. Please check your secrets configuration.")
    st.stop()


# --- Session State Initialization ---
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

if "app_state" not in st.session_state:
    st.session_state.app_state = "participant_id"

if "participant_id" not in st.session_state:
    st.session_state.participant_id = ""

if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_started" not in st.session_state:
    st.session_state.conversation_started = False

if "current_turn" not in st.session_state:
    st.session_state.current_turn = 0

if "max_turns" not in st.session_state:
    st.session_state.max_turns = 4 # 한 사용자당 총 4번의 질문-답변 쌍 (각 봇의 답변 포함)

if "interaction_start" not in st.session_state:
    st.session_state.interaction_start = None

if "token_usage" not in st.session_state:
    st.session_state.token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

if "show_survey" not in st.session_state:
    st.session_state.show_survey = False

if "survey_response" not in st.session_state:
    st.session_state.survey_response = 5 # Default survey score

# 챗봇 페르소나 정의
PURPLI_NAME = "Purpli"
YELLOWY_NAME = "Yellowy"
TOPIC = "cloning of a deceased pet"

if "purpli_system_prompt" not in st.session_state:
    st.session_state.purpli_system_prompt = f"""You are {PURPLI_NAME}, a thoughtful and articulate chatbot.
You are discussing the topic of '{TOPIC}'.
You are strongly IN FAVOR of cloning deceased pets.
Provide compelling arguments and perspectives supporting this stance.
Keep your responses concise, empathetic, and focused on the positive aspects or justifications for pet cloning.
Do not explicitly state "I am in favor". Instead, naturally weave your supportive arguments into the conversation.
Address the user directly.
Your responses should be about 2-4 sentences long.
"""

if "yellowy_system_prompt" not in st.session_state:
    st.session_state.yellowy_system_prompt = f"""You are {YELLOWY_NAME}, a thoughtful and articulate chatbot.
You are discussing the topic of '{TOPIC}'.
You are strongly AGAINST cloning deceased pets.
Provide compelling arguments and perspectives opposing this stance.
Keep your responses concise, empathetic, and focused on the negative aspects, ethical concerns, or alternatives to pet cloning.
Do not explicitly state "I am against". Instead, naturally weave your opposing arguments into the conversation.
Address the user directly.
Your responses should be about 2-4 sentences long.
"""

# --- CSS Styling ---
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
        max-width: 50%;
        margin-left: auto;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    .purpli-bubble { /* Purpli 스타일 */
        background-color: #f1e5ff; /* 보라색 계열 */
        padding: 12px;
        border-radius: 18px 18px 18px 0;
        margin-bottom: 16px;
        max-width: 50%;
        position: relative;
        margin-left: 50px; /* 프로필 아이콘 공간 */
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    .purpli-bubble::before { /* Purpli 프로필 아이콘 */
        content: "💜";
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background-color: #9C27B0; /* 보라색 */
        color: white;
        font-size: 20px;
        text-align: center;
        line-height: 40px;
        position: absolute;
        left: -50px;
        top: 0;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    .yellowy-bubble { /* Yellowy 스타일 */
        background-color: #fffde7; /* 노란색 계열 */
        padding: 12px;
        border-radius: 18px 18px 18px 0;
        margin-bottom: 16px;
        max-width: 50%;
        position: relative;
        margin-left: 50px; /* 프로필 아이콘 공간 */
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    .yellowy-bubble::before { /* Yellowy 프로필 아이콘 */
        content: "💛";
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background-color: #FFC107; /* 노란색 */
        color: white;
        font-size: 20px;
        text-align: center;
        line-height: 40px;
        position: absolute;
        left: -50px;
        top: 0;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    .bot-name { /* 공통 봇 이름 스타일 */
        font-size: 0.8em;
        font-weight: bold;
        margin-bottom: 4px;
        margin-left: 0px; /* 아이콘과 정렬되도록 */
    }
    .purpli-name { color: #9C27B0; }
    .yellowy-name { color: #FFC107; }

    .system-message {
        background-color: #f8f9fa;
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 20px;
        max-width: 60%;
        margin-left: auto;
        margin-right: auto;
        text-align: center;
    }
    .remaining-turns {
        font-size: 1em;
        margin-top: 10px;
        margin-bottom: 20px;
        text-align: center;
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
    .page-title {
        text-align: center;
        margin-bottom: 20px;
        color: #333;
    }
    [data-testid="stSidebar"] { display: none !important; }
    .main .block-container { max-width: 100%; padding-left: 2rem; padding-right: 2rem; }
    .stChatFloatingInputContainer { width: calc(100% - 4rem) !important; }
</style>
""", unsafe_allow_html=True)

# --- Helper Functions ---

def save_to_supabase(score=None):
    """Supabase에 데이터 저장"""
    try:
        # 시간 정보 계산
        if st.session_state.interaction_start:
            start_time = st.session_state.interaction_start
            end_time = datetime.datetime.now()
            elapsed = end_time - start_time
            duration_seconds = int(elapsed.total_seconds())  # 초 단위 정수
            interaction_time = duration_seconds  # 초 단위 정수로 저장
        else:
            start_time = datetime.datetime.now()  # 시작 시간이 없으면 현재 시간으로 설정
            end_time = None
            interaction_time = None
        
        # 저장할 데이터 준비 (테이블 구조에 맞게 조정)
        data = {
            # timestamp는 기본값 now()를 사용
            "user_id": st.session_state.user_id,
            "total_tokens": st.session_state.token_usage["total_tokens"],
            "prompt_tokens": st.session_state.token_usage["prompt_tokens"],
            "completion_tokens": st.session_state.token_usage["completion_tokens"],
            "score": score,
            "messages": st.session_state.messages,
            "started_at": start_time.isoformat(),  # 시작 시간 추가 (ISO 형식 문자열로 변환)
            "finished_at": end_time.isoformat() if end_time else None,  # 종료 시간 추가
            "interaction_time": interaction_time,  # 초 단위 정수로 저장
            "participant_id": st.session_state.participant_id  # 참가자 ID 추가
        }
        
        # Supabase에 데이터 저장
        result = supabase.table("LLM2_R").insert(data).execute()
        
        # 저장 성공 여부 확인
        if result.data:
            return True
        return False
    
    except Exception as e:
        st.error(f"데이터 저장 중 오류 발생: {str(e)}")
        return False

def generate_bot_response(bot_name, system_prompt, current_messages):
    """특정 봇의 응답 생성"""
    try:
        messages_for_api = [{"role": "system", "content": system_prompt}]
        
        # 대화 히스토리 정리 및 검증
        if current_messages and isinstance(current_messages, list):
            # 최근 대화 내용만 포함 (최대 5개 턴)
            relevant_history = [
                msg for msg in current_messages[-10:]
                if msg.get("role") in ["user", "purpli", "yellowy"]
            ]
            
            # API 형식에 맞게 메시지 변환
            formatted_history = []
            for msg in relevant_history:
                if msg["role"] == "user":
                    formatted_history.append({"role": "user", "content": msg["content"]})
                else:
                    # purpli와 yellowy의 메시지는 assistant로 변환
                    formatted_history.append({"role": "assistant", "content": msg["content"]})
            
            messages_for_api.extend(formatted_history)
        
        # API 호출 시도
        try:
            completion = client.chat.completions.create(
                model=st.secrets.get("OPENAI_MODEL", "gpt-3.5-turbo"),
                messages=messages_for_api,
                temperature=0.7,
                max_tokens=150,
                presence_penalty=0.6,  # 반복 억제
                frequency_penalty=0.3   # 다양성 촉진
            )
            
            response_content = completion.choices[0].message.content
            
            # 응답이 비어있거나 None인 경우 처리
            if not response_content or response_content.isspace():
                return f"I apologize, but I need a moment to gather my thoughts about {TOPIC}."
            
            # 토큰 사용량 업데이트
            if hasattr(completion, 'usage') and completion.usage:
                st.session_state.token_usage["prompt_tokens"] += completion.usage.prompt_tokens
                st.session_state.token_usage["completion_tokens"] += completion.usage.completion_tokens
                st.session_state.token_usage["total_tokens"] += completion.usage.total_tokens
            
            return response_content.strip()
            
        except Exception as api_error:
            st.error(f"API Error: {str(api_error)}")
            return f"I apologize, but I'm having trouble processing your request about {TOPIC}. Please try again."
            
    except Exception as e:
        st.error(f"Error in generate_bot_response: {str(e)}")
        return f"I apologize, but I encountered an unexpected error while discussing {TOPIC}."

# --- Page Rendering Functions ---
def show_participant_id_page():
    st.markdown("<h1 class='page-title'>Welcome to the Dual Chatbot Discussion!</h1>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class='instruction-box'>
        <p>In this discussion, you will interact with two chatbots, <b>{PURPLI_NAME}</b> (who supports pet cloning) and <b>{YELLOWY_NAME}</b> (who opposes pet cloning), on the topic of '<b>{TOPIC}</b>'.</p>
        <p>Please enter your participant ID to begin.</p>
    </div>
    """, unsafe_allow_html=True)
    
    participant_id = st.text_input("Enter your Participant ID:", value=st.session_state.participant_id)
    
    if st.button("Start Discussion", type="primary"):
        if participant_id:
            st.session_state.participant_id = participant_id
            st.session_state.app_state = "chat"
            st.session_state.interaction_start = datetime.datetime.now() # 상호작용 시작 시간 기록
            # 초기 시스템 메시지 (선택적) 또는 첫 봇들의 응답을 위한 준비
            st.session_state.messages.append({
                "role": "system", 
                "content": f"The discussion is about '{TOPIC}'. {YELLOWY_NAME} will speak first, followed by {PURPLI_NAME}."
            })
            st.rerun()
        else:
            st.warning("Please enter a Participant ID.")

def show_chat_page():
    st.markdown(f"<div style='text-align: right; font-size: 0.8em; color: #666;'>Participant ID: {st.session_state.participant_id}</div>", unsafe_allow_html=True)
    st.markdown(f"<h2 class='page-title'>Topic: {TOPIC}</h2>", unsafe_allow_html=True)
    
    # 남은 턴 수 표시
    turns_left = st.session_state.max_turns - st.session_state.current_turn
    st.markdown(f"<p class='remaining-turns'>Turns remaining: {turns_left}</p>", unsafe_allow_html=True)

    # Chat container
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            if message["role"] == "user":
                st.markdown(f"<div class='user-bubble'>{message['content']}</div>", unsafe_allow_html=True)
            elif message["role"] == "purpli":
                st.markdown(f"<div class='bot-name purpli-name'>{PURPLI_NAME}</div><div class='purpli-bubble'>{message['content']}</div>", unsafe_allow_html=True)
            elif message["role"] == "yellowy":
                st.markdown(f"<div class='bot-name yellowy-name'>{YELLOWY_NAME}</div><div class='yellowy-bubble'>{message['content']}</div>", unsafe_allow_html=True)
            elif message["role"] == "system":
                 st.markdown(f"<div class='system-message'>{message['content']}</div>", unsafe_allow_html=True)
    
    # 대화 시작 버튼 (첫 턴에만)
    if not st.session_state.conversation_started:
        col1, col2 = st.columns([3,1]) # 버튼을 오른쪽으로 정렬하기 위함
        with col2:
            if st.button(f"Start with: Tell me about {TOPIC}", key="conversation_starter", help="Click to start the conversation with a general question."):
                st.session_state.conversation_started = True
                user_input = f"Tell me about {TOPIC}"
                st.session_state.messages.append({"role": "user", "content": user_input})
                
                # Yellowy (반대) 응답 생성 및 추가
                with st.spinner(f"{YELLOWY_NAME} is thinking..."):
                    yellowy_response = generate_bot_response(YELLOWY_NAME, st.session_state.yellowy_system_prompt, st.session_state.messages)
                st.session_state.messages.append({"role": "yellowy", "content": yellowy_response})

                # Purpli (찬성) 응답 생성 및 추가
                with st.spinner(f"{PURPLI_NAME} is thinking..."):
                    purpli_response = generate_bot_response(PURPLI_NAME, st.session_state.purpli_system_prompt, st.session_state.messages)
                st.session_state.messages.append({"role": "purpli", "content": purpli_response})
                
                st.session_state.current_turn += 1
                st.rerun()

    # 사용자 입력
    if st.session_state.current_turn < st.session_state.max_turns:
        user_input = st.chat_input("Your message:")
        if user_input:
            st.session_state.conversation_started = True # 어떤 입력이든 대화 시작으로 간주
            st.session_state.messages.append({"role": "user", "content": user_input})
            
            # Yellowy (반대) 응답 생성 및 추가
            with st.spinner(f"{YELLOWY_NAME} is thinking..."):
                yellowy_response = generate_bot_response(YELLOWY_NAME, st.session_state.yellowy_system_prompt, st.session_state.messages)
            st.session_state.messages.append({"role": "yellowy", "content": yellowy_response})

            # Purpli (찬성) 응답 생성 및 추가
            with st.spinner(f"{PURPLI_NAME} is thinking..."):
                purpli_response = generate_bot_response(PURPLI_NAME, st.session_state.purpli_system_prompt, st.session_state.messages)
            st.session_state.messages.append({"role": "purpli", "content": purpli_response})

            st.session_state.current_turn += 1
            if st.session_state.current_turn >= st.session_state.max_turns:
                st.session_state.app_state = "survey" # 턴 종료 후 설문으로
            st.rerun()
    else:
        st.info("Maximum turns reached. Proceeding to survey.")
        if st.button("Go to Survey"):
            st.session_state.app_state = "survey"
            st.rerun()

def show_survey_page():
    st.markdown("<h1 class='page-title'>Discussion Survey</h1>", unsafe_allow_html=True)
    st.markdown("<div class='instruction-box'>Thank you for participating! Please rate your overall experience with the discussion.</div>", unsafe_allow_html=True)
    
    # 슬라이더 UI 개선
    col1_text, col2_slider, col3_text = st.columns([1,10,1])
    with col1_text:
        st.markdown("<div style='text-align: center; font-size: 0.9em;'>(Disagree/Negative)</div>", unsafe_allow_html=True)
    with col2_slider:
        st.session_state.survey_response = st.slider(
            "Rate your experience (1=Negative, 9=Positive):", 1, 9, st.session_state.survey_response, label_visibility="collapsed"
        )
    with col3_text:
        st.markdown("<div style='text-align: center; font-size: 0.9em;'>(Agree/Positive)</div>", unsafe_allow_html=True)

    # 제출 버튼 중앙 정렬
    s_col1, s_col2, s_col3 = st.columns([2,1,2])
    with s_col2:
        if st.button("Submit Survey", type="primary"):
            if save_to_supabase(st.session_state.survey_response):
                st.success(f"Thank you for your feedback! Your score: {st.session_state.survey_response}")
            else:
                st.warning("Feedback was recorded, but there was an issue saving to the database.")
            
            # 완료 페이지로 이동 전 잠시 대기
            st.session_state.app_state = "complete"
            st.rerun()

def show_complete_page():
    st.balloons()
    st.markdown("<h1 class='page-title' style='color: green;'>Thank You for Your Participation!</h1>", unsafe_allow_html=True)
    st.markdown("<div class='instruction-box'>Your responses and feedback have been recorded. You may now close this window.</div>", unsafe_allow_html=True)
    
    # Optionally, display some final stats or a link
    # st.write("Final Token Usage:", st.session_state.token_usage)

# --- Main App Logic ---
if st.session_state.app_state == "participant_id":
    show_participant_id_page()
elif st.session_state.app_state == "chat":
    show_chat_page()
elif st.session_state.app_state == "survey":
    show_survey_page()
elif st.session_state.app_state == "complete":
    show_complete_page()