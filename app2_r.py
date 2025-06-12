import os
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import json
import glob
import datetime  # For time measurement
import time  # Add this import for time.sleep()
import uuid
from supabase import create_client, Client


# Load environment variables from .env file
load_dotenv()


# Page configuration
st.set_page_config(
    page_title="Debate Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"  # 사이드바 기본 숨김 상태로 설정
)


# Initialize app state (to switch between chat and survey)
# 참가자 ID 관리
if "participant_id" not in st.session_state:
    st.session_state.participant_id = ""


# 앱 상태 기본값을 participant_id로 변경
if "app_state" not in st.session_state:
    st.session_state.app_state = "participant_id"  # 'participant_id', 'chat', 'survey', or 'complete'


# Initialize session state variables if they don't exist
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "You will engage in a four-turn conversation with a chatbot about \"Cloning of a deceased pet\". Click the button with the question to begin the first turn. After that, you will have three more turns to continue the conversation by typing freely. Start the conversation — Purpli and Yellowy will respond together.", "type": "system"}]


if "system_message_pro" not in st.session_state:
    st.session_state.system_message_pro = "You are 'Purpli', a debater who takes a supportive stance on cloning a deceased pet. Please provide logical and persuasive opinions in favor of the topic. Answer in simple 4 sentences."


if "system_message_con" not in st.session_state:
    st.session_state.system_message_con = "You are 'Yellowy', who takes an opposing stance on cloning a deceased pet. Please provide logical and persuasive opinions against the topic. Answer in simple 4 sentences."


if "usage_stats" not in st.session_state:
    st.session_state.usage_stats = []


if "show_process" not in st.session_state:
    st.session_state.show_process = False


# Session time measurement variables
if "session_start_time" not in st.session_state:
    st.session_state.session_start_time = datetime.datetime.now()


if "last_interaction_time" not in st.session_state:
    st.session_state.last_interaction_time = datetime.datetime.now()


if "total_session_duration" not in st.session_state:
    st.session_state.total_session_duration = datetime.timedelta(0)


if "interaction_count" not in st.session_state:
    st.session_state.interaction_count = 0


# Add conversation variables
if "conversation_started" not in st.session_state:
    st.session_state.conversation_started = False


if "current_turn" not in st.session_state:
    st.session_state.current_turn = 0


# 턴 수 설정 변수
if "max_turns" not in st.session_state:
    st.session_state.max_turns = 4  # 기본값


# Survey response
if "survey_response" not in st.session_state:
    st.session_state.survey_response = 5  # 기본값 (중간)


# 사용자 ID 생성 (세션 시작시 한번만)
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())


# 상호작용 시작 시간 추적을 위한 변수
if "interaction_start" not in st.session_state:
    st.session_state.interaction_start = None


# 토큰 사용량 추적을 위한 변수
if "token_usage" not in st.session_state:
    st.session_state.token_usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}


# Supabase 클라이언트 초기화
supabase_url = st.secrets["SUPABASE_URL"]
supabase_key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(supabase_url, supabase_key)


# Usage time tracking function
def update_session_time():
    """Updates the usage time of the current session"""
    now = datetime.datetime.now()
   
    # If more than 10 minutes (600 seconds) have passed since the last interaction, consider it a new session
    time_diff = (now - st.session_state.last_interaction_time).total_seconds()
    if time_diff > 600:  # More than 10 minutes difference
        # Save previous session time
        session_duration = st.session_state.last_interaction_time - st.session_state.session_start_time
        st.session_state.total_session_duration += session_duration
       
        # Start new session
        st.session_state.session_start_time = now
   
    # Update last interaction time
    st.session_state.last_interaction_time = now
   
    # Increase interaction count
    st.session_state.interaction_count += 1


def get_openai_client():
    """Create and return an OpenAI client configured with secret values"""
    try:
        token = st.secrets["OPENAI_API_KEY"]
        endpoint = st.secrets["OPENAI_API_BASE"]
    except KeyError as e:
        st.error(f"필수 secret 값이 누락되었습니다: {str(e)}")
        st.stop()

    if not token or not endpoint:
        st.error("OpenAI API key 또는 endpoint가 비어 있습니다. secrets.toml 파일을 확인해주세요.")
        st.stop()

    return OpenAI(
        base_url=endpoint,
        api_key=token,
    )



def generate_debate_responses(prompt):
    """Generate two separate responses - one pro, one con"""
    # Update interaction time
    update_session_time()
   
    client = get_openai_client()
    model_name = st.secrets["OPENAI_API_MODEL"]
   
    # Prepare previous conversation history (excluding the system message)
    history = []
    for msg in st.session_state.messages:
        if msg["role"] != "system" and "type" not in msg:  # Skip system messages
            history.append(msg)
   
    # Generate pro messages
    pro_messages = [{"role": "system", "content": st.session_state.system_message_pro}] + history + [{"role": "user", "content": prompt}]
   
    # Generate con messages
    con_messages = [{"role": "system", "content": st.session_state.system_message_con}] + history + [{"role": "user", "content": prompt}]
   
    try:
        # Display response in chat format
        status_placeholder = st.empty()
        status_placeholder.markdown("Generating response...", unsafe_allow_html=True)
        
        # 반대 의견 먼저 생성 (원래 코드에서는 찬성 의견이 먼저였음)
        full_con_response = ""
        usage_con = None
        
        con_response = client.chat.completions.create(
            messages=con_messages,
            model=model_name,
            stream=True,
            stream_options={'include_usage': True}
        )
        
        # Add con response
        con_placeholder = st.empty()
        
        # Stream con response
        for chunk in con_response:
            if chunk.choices and chunk.choices[0].delta.content:
                content_chunk = chunk.choices[0].delta.content
                full_con_response += content_chunk
                con_placeholder.markdown(
                    f"<div class='con-name'>Yellowy</div><div class='con-bubble'>{full_con_response}▌</div>",
                    unsafe_allow_html=True
                )
                
            if chunk.usage:
                usage_con = chunk.usage
        
        # Update final con response (remove cursor)
        con_placeholder.markdown(
            f"<div class='con-name'>Yellowy</div><div class='con-bubble'>{full_con_response}</div>",
            unsafe_allow_html=True
        )
        
        # 그 다음 찬성 의견 생성
        full_pro_response = ""
        usage_pro = None
        
        pro_response = client.chat.completions.create(
            messages=pro_messages,
            model=model_name,
            stream=True,
            stream_options={'include_usage': True}
        )
        
        # Add pro response
        pro_placeholder = st.empty()
        
        # Stream pro response
        for chunk in pro_response:
            if chunk.choices and chunk.choices[0].delta.content:
                content_chunk = chunk.choices[0].delta.content
                full_pro_response += content_chunk
                pro_placeholder.markdown(
                    f"<div class='pro-name'>Purpli</div><div class='pro-bubble'>{full_pro_response}▌</div>",
                    unsafe_allow_html=True
                )
                
            if chunk.usage:
                usage_pro = chunk.usage
        
        # Update final pro response (remove cursor)
        pro_placeholder.markdown(
            f"<div class='pro-name'>Purpli</div><div class='pro-bubble'>{full_pro_response}</div>",
            unsafe_allow_html=True
        )
        
        # Remove status display
        status_placeholder.empty()
        
        # 메시지 추가 순서도 변경 - 반대 의견을 먼저 추가
        st.session_state.messages.append({"role": "assistant", "content": full_con_response, "type": "con"})
        st.session_state.messages.append({"role": "assistant", "content": full_pro_response, "type": "pro"})
       
        # Save usage statistics
        if usage_pro and usage_con:
            # Handle Pydantic models
            usage_pro_dict = usage_pro.model_dump() if hasattr(usage_pro, 'model_dump') else usage_pro.dict()
            usage_con_dict = usage_con.model_dump() if hasattr(usage_con, 'model_dump') else usage_con.dict()
           
            st.session_state.usage_stats.append({
                "prompt_tokens": usage_pro_dict.get("prompt_tokens", 0) + usage_con_dict.get("prompt_tokens", 0),
                "completion_tokens": usage_pro_dict.get("completion_tokens", 0) + usage_con_dict.get("completion_tokens", 0),
                "total_tokens": usage_pro_dict.get("total_tokens", 0) + usage_con_dict.get("total_tokens", 0)
            })
       
        # If process display is activated
        if st.session_state.show_process:
            process_container = st.container()
            with process_container:
                st.markdown("### Model Processing")
               
                # Display request details
                request_expander = st.expander("Request Details", expanded=False)
                with request_expander:
                    st.markdown("**Pro System Message:**")
                    st.code(st.session_state.system_message_pro)
                    st.markdown("**Con System Message:**")
                    st.code(st.session_state.system_message_con)
                    st.markdown("**User Input:**")
                    st.code(prompt)
               
                # Display raw responses
                response_expander = st.expander("Raw Responses", expanded=False)
                with response_expander:
                    st.markdown("**Pro Response:**")
                    st.code(full_pro_response, language="markdown")
                    st.markdown("**Con Response:**")
                    st.code(full_con_response, language="markdown")
               
                # Display usage statistics
                if usage_pro and usage_con:
                    usage_expander = st.expander("Usage Statistics", expanded=False)
                    with usage_expander:
                        st.markdown("**Pro Response Usage:**")
                        st.markdown(f"- Prompt tokens: {usage_pro_dict.get('prompt_tokens', 0)}")
                        st.markdown(f"- Completion tokens: {usage_pro_dict.get('completion_tokens', 0)}")
                        st.markdown(f"- Total tokens: {usage_pro_dict.get('total_tokens', 0)}")
                       
                        st.markdown("**Con Response Usage:**")
                        st.markdown(f"- Prompt tokens: {usage_con_dict.get('prompt_tokens', 0)}")
                        st.markdown(f"- Completion tokens: {usage_con_dict.get('completion_tokens', 0)}")
                        st.markdown(f"- Total tokens: {usage_con_dict.get('total_tokens', 0)}")
       
        # 턴 수 증가
        st.session_state.current_turn += 1
       
        return True
    except Exception as e:
        st.error(f"Error generating responses: {str(e)}")
        return False


# CSS style definition
st.markdown("""
    <style>
    .pro-bubble {
        background-color: #f1e5ff;
        padding: 12px;
        border-radius: 18px 18px 18px 0;
        margin-bottom: 16px;
        max-width: 50%;  /* 68%에서 50%로 변경 */
        position: relative;
        margin-left: 50px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }


    .pro-bubble::before {
        content: "";
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background-color: #9C27B0;  /* Purple color */
        position: absolute;
        left: -50px;
        top: 0;
        background-image: url('https://cdn-icons-png.flaticon.com/512/4712/4712035.png');
        background-size: 60%;
        background-position: center;
        background-repeat: no-repeat;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }


    .con-bubble {
        background-color: #fffde7;
        padding: 12px;
        border-radius: 18px 18px 18px 0;
        margin-bottom: 16px;
        max-width: 50%;  /* 68%에서 50%로 변경 */
        position: relative;
        margin-left: 50px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }


    .con-bubble::before {
        content: "";
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background-color: #FFC107;  /* Yellow color */
        position: absolute;
        left: -50px;
        top: 0;
        background-image: url('https://cdn-icons-png.flaticon.com/512/4712/4712035.png');
        background-size: 60%;
        background-position: center;
        background-repeat: no-repeat;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }


    .user-bubble {
        background-color: #e3f0fd;
        padding: 12px;
        border-radius: 18px 18px 0 18px;
        margin-bottom: 16px;
        text-align: left;
        max-width: 50%;  /* 60%에서 50%로 변경 */
        margin-left: auto;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }


    .system-bubble {
        background-color: #f8f9fa;
        padding: 12px;
        border-radius: 18px;
        margin-bottom: 16px;
        max-width: 60%;  /* 70%에서 60%로 변경 */
        margin-left: auto;
        margin-right: auto;
        text-align: center;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }


    .stChatFloatingInputContainer {
        position: fixed !important;
        bottom: 0 !important;
        padding: 1rem !important;
        width: calc(100% - 250px) !important; /* Sidebar width adjustment */
        background-color: white !important;
        z-index: 1000 !important;
    }


    .main-content {
        padding-bottom: 100px; /* Bottom margin for fixed input container */
    }


    .pro-name {
        font-size: 0.8em;
        color: #9C27B0;  /* Purple color */
        font-weight: bold;
        margin-bottom: 4px;
        margin-left: 0px;
    }


    .con-name {
        font-size: 0.8em;
        color: #FFC107;  /* Yellow color */
        font-weight: bold;
        margin-bottom: 4px;
        margin-left: 0px;
    }
   
    .starter-btn-box {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 15px;
    }
   
    .next-button {
        background-color: #4CAF50;
        color: white;
        border: none;
        padding: 10px 20px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 16px;
        margin: 20px 0;
        cursor: pointer;
        border-radius: 5px;
    }
   
    .survey-container {
        max-width: 800px;
        margin: 50px auto;
        padding: 30px;
        background-color: #f9f9f9;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
   
    .survey-title {
        font-size: 24px;
        margin-bottom: 30px;
        text-align: center;
    }
   
    .slider-labels {
        display: flex;
        justify-content: space-between;
        margin-top: 5px;
        color: #666;
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


# Supabase에 데이터 저장 함수 추가
def save_to_supabase(score=None):
    """Supabase의 LLM2 테이블에 데이터 저장"""
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
       
        # 토큰 사용량 계산 (사용 통계에서 계산)
        if st.session_state.usage_stats:
            total_prompt = sum(u["prompt_tokens"] for u in st.session_state.usage_stats)
            total_completion = sum(u["completion_tokens"] for u in st.session_state.usage_stats)
            total_tokens = sum(u["total_tokens"] for u in st.session_state.usage_stats)
        else:
            total_prompt = 0
            total_completion = 0
            total_tokens = 0
       
        # 저장할 데이터 준비 (테이블 구조에 맞게 조정)
        data = {
            # timestamp는 기본값 now()를 사용
            "user_id": st.session_state.user_id,
            "participant_id": st.session_state.participant_id,  # 참가자 ID 추가
            "started_at": start_time.isoformat() if start_time else None,  # 시작 시간 추가 (ISO 형식 문자열로 변환)
            "finished_at": end_time.isoformat() if end_time else None,  # 종료 시간 추가
            "interaction_time": interaction_time,  # 초 단위 정수로 저장
            "total_tokens": total_tokens,
            "prompt_tokens": total_prompt,
            "completion_tokens": total_completion,
            "score": score,
            "messages": st.session_state.messages
        }
       
        # Supabase에 데이터 저장 (LLM2_R 테이블에 저장)
        result = supabase.table("LLM2_R").insert(data).execute()
       
        # 저장 성공 여부 확인
        if result.data:
            return True
        return False
   
    except Exception as e:
        st.error(f"데이터 저장 중 오류 발생: {str(e)}")
        return False


# 참가자 ID 검증 함수 추가
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


# 참가자 ID 입력 페이지 함수 수정
def show_participant_id_page():
    st.title("Participant Information")
   
    col1, col2, col3 = st.columns([1, 2, 1])
   
    with col2:
        st.markdown("### Please enter your participant ID")
        st.markdown("Enter the participant ID provided for this experiment.")
       
        # Participant ID input field (입력 예시 및 규칙 제거)
        participant_id = st.text_input(
            "Participant ID",
            value=st.session_state.participant_id,
            key="participant_id_input"
        )
       
        # Start experiment button
        if st.button("Start Experiment", type="primary", key="start_experiment_btn"):
            st.session_state.participant_id = participant_id

            # DB에 참가자 번호 저장 (유효성 검사 없이)
            try:
                supabase.table("participants").insert({
                    "id": participant_id,
                    "created_at": datetime.datetime.now().isoformat()
                }).execute()
            except Exception as e:
                st.warning(f"Could not save participant ID to DB: {e}")

            st.session_state.app_state = "chat"
            st.success("Participant ID saved. You can start chatting!")
            time.sleep(1)
            st.rerun()


# 대화 페이지
def show_chat_page():
    # 상단에 참가자 ID 표시 추가
    st.markdown(f"<div style='text-align: right; font-size: 0.8em; color: #666;'>Participant ID: {st.session_state.participant_id}</div>", unsafe_allow_html=True)
   
    # Sidebar settings
    with st.sidebar:
        st.subheader("Settings")
       
        # 대화 턴 수 설정 슬라이더 추가
        st.session_state.max_turns = st.slider(
            "Number of conversation turns",
            min_value=1,
            max_value=10,
            value=st.session_state.max_turns,
            step=1
        )
       
        st.markdown(f"**Current turn: {st.session_state.current_turn}/{st.session_state.max_turns}**")
       
        # Display time statistics
        with st.expander("Usage Time Statistics", expanded=False):
            # Calculate current session
            current_session_duration = st.session_state.last_interaction_time - st.session_state.session_start_time
            total_time = st.session_state.total_session_duration + current_session_duration
           
            # Format time (hours:minutes:seconds)
            def format_timedelta(td):
                total_seconds = int(td.total_seconds())
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                seconds = total_seconds % 60
                return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
           
            st.write("### Usage Time")
            st.write(f"Current session: {format_timedelta(current_session_duration)}")
            st.write(f"Total usage time: {format_timedelta(total_time)}")
            st.write(f"Total interactions: {st.session_state.interaction_count}")
            st.write(f"First usage time: {st.session_state.session_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            st.write(f"Last usage time: {st.session_state.last_interaction_time.strftime('%Y-%m-%d %H:%M:%S')}")
       
        # Edit pro system message
        st.text_area(
            "Pro Chatbot Settings",
            value=st.session_state.system_message_pro,
            key="system_message_pro_input",
            height=150
        )
       
        # Edit con system message
        st.text_area(
            "Con Chatbot Settings",
            value=st.session_state.system_message_con,
            key="system_message_con_input",
            height=150
        )
       
        if st.button("Update System Messages"):
            st.session_state.system_message_pro = st.session_state.system_message_pro_input
            st.session_state.system_message_con = st.session_state.system_message_con_input
            st.success("System messages have been updated!")
       
        # Other sidebar elements
        st.markdown("---")
       
        # View chat history
        with st.expander("View Chat History"):
            st.json(st.session_state.messages)
       
        # View usage statistics
        with st.expander("View Usage Statistics"):
            if st.session_state.usage_stats:
                for i, usage in enumerate(st.session_state.usage_stats):
                    st.write(f"Message {i+1}:")
                    st.write(f"- Prompt tokens: {usage['prompt_tokens']}")
                    st.write(f"- Completion tokens: {usage['completion_tokens']}")
                    st.write(f"- Total tokens: {usage['total_tokens']}")
                    st.divider()
               
                # Calculate total usage
                total_prompt = sum(u["prompt_tokens"] for u in st.session_state.usage_stats)
                total_completion = sum(u["completion_tokens"] for u in st.session_state.usage_stats)
                total = sum(u["total_tokens"] for u in st.session_state.usage_stats)
               
                st.write("### Total Usage")
                st.write(f"- Total prompt tokens: {total_prompt}")
                st.write(f"- Total completion tokens: {total_completion}")
                st.write(f"- Total tokens: {total}")
            else:
                st.write("No usage data available yet.")
       
        # Reset chat button
        if st.button("Reset Chat"):
            st.session_state.messages = [{"role": "assistant", "content": "You will engage in a four-turn conversation with a chatbot about \"Cloning of a deceased pet\". Click the button with the question to begin the first turn. After that, you will have three more turns to continue the conversation by typing freely. Start the conversation — Purpli and Yellowy will respond together.", "type": "system"}]
            st.session_state.usage_stats = []
            st.session_state.conversation_started = False
            st.session_state.current_turn = 0
           
            # Reset time variables
            now = datetime.datetime.now()
            st.session_state.session_start_time = now
            st.session_state.last_interaction_time = now
            st.session_state.total_session_duration = datetime.timedelta(0)
            st.session_state.interaction_count = 0
           
            st.success("Chat history has been reset!")
       
        # Process display toggle
        st.markdown("---")
        st.session_state.show_process = st.checkbox("Show model processing", value=st.session_state.show_process)


    # Main chat area
    chat_container = st.container()
    with chat_container:
        st.markdown('<div class="main-content">', unsafe_allow_html=True)
       
        # 가장 먼저 시스템 메시지 표시
        system_message_shown = False
       
        # Process chat history in order
        i = 0
        while i < len(st.session_state.messages):
            message = st.session_state.messages[i]
           
            # 시스템 메시지는 한 번만 표시
            if message["role"] == "assistant" and "type" in message and message["type"] == "system":
                if not system_message_shown:
                    st.markdown(
                        f"<div class='system-bubble'>{message['content']}</div>",
                        unsafe_allow_html=True
                    )
                    system_message_shown = True
                   
                    # 시스템 메시지 바로 다음에 대화 스타터 버튼 배치
                    col1, col2 = st.columns([3, 1])
                    with col2:
                        if not st.session_state.conversation_started and st.button(
                            "Yellowy, Purpli, can you tell me about cloning of a deceased pet?",  # 버튼 텍스트 변경
                            key="conversation_starter"
                        ):
                            # 상호작용 시작 시간 기록
                            st.session_state.interaction_start = datetime.datetime.now()
                            
                            st.session_state.conversation_started = True
                            st.session_state.current_turn = 1
                            user_prompt = "Yellowy, Purpli, can you tell me about cloning of a deceased pet?"  # 메시지 내용도 동일하게 변경
                            st.session_state.messages.append({"role": "user", "content": user_prompt})
                           
                            # 고정된 첫 응답
                            yellowy_response = "Cloning from a deceased pet involves complex steps—DNA must be extracted from preserved tissue, then an embryo is formed and implanted into a surrogate. Even if the cloned pet looks the same and shares the same genes, it won't have the same memories or personality, and the sense of loss may still remain. There are many abandoned animals waiting to be adopted, and providing care for them may be a more meaningful choice than cloning."
                            purpli_response = "However, cloning a deceased pet involves using biotechnology to create a new animal that is genetically identical to the original. For many people, pets are like family, so the idea of meeting them again in any form can be deeply comforting. With today's advanced technology, cloning has become a realistic option. Some also believe it's worth preserving the genes of special animals—like service dogs or police dogs—through cloning."
                           
                            # 메시지 추가 순서도 변경 - 반대 의견을 먼저 추가
                            st.session_state.messages.append({"role": "assistant", "content": yellowy_response, "type": "con"})
                            st.session_state.messages.append({"role": "assistant", "content": purpli_response, "type": "pro"})
                           
                            st.rerun()
                i += 1
            elif message["role"] == "user":
                # User message
                st.markdown(
                    f"<div class='user-bubble'>{message['content']}</div>",
                    unsafe_allow_html=True
                )
                i += 1
            elif message["role"] == "assistant" and "type" in message and message["type"] == "pro":
                # Pro message - display with purple profile and name "Purpli"
                st.markdown(
                    f"<div class='pro-name'>Purpli</div><div class='pro-bubble'>{message['content']}</div>",
                    unsafe_allow_html=True
                )
                i += 1
            elif message["role"] == "assistant" and "type" in message and message["type"] == "con":
                # Con message - display with yellow profile and name "Yellowy"
                st.markdown(
                    f"<div class='con-name'>Yellowy</div><div class='con-bubble'>{message['content']}</div>",
                    unsafe_allow_html=True
                )
                i += 1
            else:
                # Other messages
                st.markdown(
                    f"<div class='system-bubble'>{message['content']}</div>",
                    unsafe_allow_html=True
                )
                i += 1
       
        # 대화 턴 수가 최대에 도달했으면 Next 버튼 표시
        if st.session_state.conversation_started and st.session_state.current_turn >= st.session_state.max_turns:
            st.markdown("<div style='text-align: center; margin-top: 30px;'>You have reached the maximum number of turns.</div>", unsafe_allow_html=True)
           
            # Next 버튼
            if st.button("Next", key="next_to_survey", type="primary"):
                st.session_state.app_state = "survey"
                st.rerun()
       
        st.markdown('</div>', unsafe_allow_html=True)


    # Chat input (Only show if conversation not finished)
    if st.session_state.conversation_started and st.session_state.current_turn < st.session_state.max_turns:
        if prompt := st.chat_input("Enter a topic you want to discuss..."):
            # Display user message without chatbot icon
            st.markdown(
                f"<div class='user-bubble'>{prompt}</div>",
                unsafe_allow_html=True
            )
           
            # Add user message to history
            st.session_state.messages.append({"role": "user", "content": prompt})
           
            # Generate and display pro/con responses
            generate_debate_responses(prompt)
           
            # Force rerun to update the UI
            st.rerun()


# 설문조사 페이지
def show_survey_page():
    st.markdown("<h2>Survey</h2>", unsafe_allow_html=True)
    st.markdown("**Do you want to talk more with this chatbot?**")
   
    # 슬라이더 UI 개선 - 3개의 열 사용
    col1, col2, col3 = st.columns([1, 10, 1])
   
    with col1:
        st.markdown("<div style='text-align: center; font-size: 0.9em;'>(Disagree)</div>", unsafe_allow_html=True)
       
    with col2:
        # 라벨 숨기기
        st.session_state.survey_response = st.slider("", 1, 9, st.session_state.survey_response, label_visibility="collapsed")
       
    with col3:
        st.markdown("<div style='text-align: center; font-size: 0.9em;'>(Agree)</div>", unsafe_allow_html=True)
   
    # 제출 버튼 중앙 정렬
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("Submit Survey", type="primary", key="survey_submit"):
            # Supabase에 데이터 저장
            if save_to_supabase(st.session_state.survey_response):
                st.success(f"Thank you for your feedback! Your score: {st.session_state.survey_response}")
            else:
                st.warning("피드백이 저장되었지만, 데이터베이스 저장에 문제가 있었습니다.")
   
            # 일정 시간 후 완료 페이지로 이동
            time.sleep(2)
   
            # 완료 페이지로 이동
            st.session_state.app_state = "complete"
            st.rerun()
   
    st.markdown("</div>", unsafe_allow_html=True)


# 설문 완료 페이지 함수 추가 (show_survey_page 함수 다음에 추가)
def show_complete_page():
    # 중앙 정렬을 위한 컬럼 사용
    col1, col2, col3 = st.columns([1, 2, 1])
   
    with col2:
        st.markdown("<h1 style='text-align: center; margin-top: 100px;'>Thank you for your participation!</h1>", unsafe_allow_html=True)
       
        # 다시 시작 버튼 (옵션)
        st.markdown("<div style='text-align: center; margin-top: 50px;'>", unsafe_allow_html=True)
        if st.button("Start a new conversation", type="primary", key="restart_btn"):
            # 대화 페이지로 돌아가기 및 초기화
            st.session_state.app_state = "chat"
            st.session_state.messages = [{"role": "assistant", "content": "You will engage in a four-turn conversation with a chatbot about \"Cloning of a deceased pet\". Click the button with the question to begin the first turn. After that, you will have three more turns to continue the conversation by typing freely. Start the conversation — Purpli and Yellowy will respond together.", "type": "system"}]
            st.session_state.conversation_started = False
            st.session_state.current_turn = 0
            st.session_state.interaction_start = None  # 시작 시간 초기화
            st.session_state.usage_stats = []  # 사용 통계 초기화
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)


# 앱 상태에 따라 적절한 페이지 표시
if st.session_state.app_state == "participant_id":
    show_participant_id_page()
elif st.session_state.app_state == "chat":
    show_chat_page()
elif st.session_state.app_state == "survey":
    show_survey_page()
elif st.session_state.app_state == "complete":
    show_complete_page()

