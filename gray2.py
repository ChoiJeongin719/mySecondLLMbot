import os
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import json
import glob
import datetime  # For time measurement

# Load environment variables from .env file
load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Debate Chatbot",
    page_icon="🤖",
    layout="wide"
)

# Initialize app state (to switch between chat and survey)
if "app_state" not in st.session_state:
    st.session_state.app_state = "chat"  # 'chat' or 'survey'

# Initialize session state variables if they don't exist
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "You will engage in a four-turn conversation with a chatbot about \"Cloning of a deceased pet\". Click the button with the question to begin the first turn. After that, you will have three more turns to continue the conversation by typing freely. Start the conversation — Purpli and Yellowy will respond together.", "type": "system"}]

if "system_message_pro" not in st.session_state:
    st.session_state.system_message_pro = "You are a debater who takes a supportive stance on the topic presented by the user. Please provide logical and persuasive opinions in favor of the topic. Answer in 4 sentences or less."

if "system_message_con" not in st.session_state:
    st.session_state.system_message_con = "You are a debater who takes an opposing stance on the topic presented by the user. Please provide logical and persuasive opinions against the topic. Answer in 4 sentences or less."

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
    """Create and return an OpenAI client configured with environment variables"""
    token = os.getenv("GITHUB_TOKEN")
    endpoint = os.getenv("GITHUB_ENDPOINT", "https://models.github.ai/inference")
    
    if not token:
        st.error("GitHub token not found in environment variables. Please check your .env file.")
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
    model_name = os.getenv("GITHUB_MODEL", "openai/gpt-4o")
    
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
        
        # Generate pro response
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
        
        # Generate con response
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
        
        # Remove status display
        status_placeholder.empty()
        
        # Add responses to session state
        st.session_state.messages.append({"role": "assistant", "content": full_pro_response, "type": "pro"})
        st.session_state.messages.append({"role": "assistant", "content": full_con_response, "type": "con"})
        
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
        background-color: #f5f5f5;  /* 밝은 회색으로 변경 */
        padding: 12px;
        border-radius: 18px 18px 18px 0;
        margin-bottom: 16px;
        max-width: 68%;
        position: relative;
        margin-left: 50px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }

    .pro-bubble::before {
        content: "";
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background-color: #9C27B0;  /* 보라색 유지 */
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
        background-color: #f5f5f5;  /* 동일한 밝은 회색으로 변경 */
        padding: 12px;
        border-radius: 18px 18px 18px 0;
        margin-bottom: 16px;
        max-width: 68%;
        position: relative;
        margin-left: 50px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }

    .con-bubble::before {
        content: "";
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background-color: #FFC107;  /* 노란색 유지 */
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
        max-width: 60%;
        margin-left: auto;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }

    .system-bubble {
        background-color: #f8f9fa;
        padding: 12px;
        border-radius: 18px;
        margin-bottom: 16px;
        max-width: 70%;
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
        color: #9C27B0;  /* 보라색 유지 */
        font-weight: bold;
        margin-bottom: 4px;
        margin-left: 0px;
    }

    .con-name {
        font-size: 0.8em;
        color: #FFC107;  /* 노란색 유지 */
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
    </style>
""", unsafe_allow_html=True)

# 대화 페이지
def show_chat_page():
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
                            "Explain about 'Pet Cloning'",
                            key="conversation_starter"
                        ):
                            st.session_state.conversation_started = True
                            st.session_state.current_turn = 1
                            user_prompt = "Explain about 'Pet cloning'"
                            st.session_state.messages.append({"role": "user", "content": user_prompt})
                            
                            # 고정된 첫 응답
                            purpli_response = "Cloning a deceased pet involves using biotechnology to create a new animal that is genetically identical to the original. For many people, pets are like family, so the idea of meeting them again in any form can be deeply comforting. With today's advanced technology, cloning has become a realistic option. Some also believe it's worth preserving the genes of special animals—like service dogs or police dogs—through cloning."
                            yellowy_response = "Cloning from a deceased pet involves complex steps—DNA must be extracted from preserved tissue, then an embryo is formed and implanted into a surrogate. Even if the cloned pet looks the same and shares the same genes, it won't have the same memories or personality, and the sense of loss may still remain. There are many abandoned animals waiting to be adopted, and providing care for them may be a more meaningful choice than cloning."
                            
                            st.session_state.messages.append({"role": "assistant", "content": purpli_response, "type": "pro"})
                            st.session_state.messages.append({"role": "assistant", "content": yellowy_response, "type": "con"})
                            
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
            st.success(f"Thank you for your feedback! Your score: {st.session_state.survey_response}")
            
            # 여기에 결과 저장 로직 추가 가능
            # (Supabase 연동 코드를 추가하려면 app.py의 save_to_supabase 함수도 가져와야 함)
            
            # 일정 시간 후 채팅으로 돌아가기
            time.sleep(2)
            
            # 대화 페이지로 돌아가기 및 초기화
            st.session_state.app_state = "chat"
            st.session_state.messages = [{"role": "assistant", "content": "You will engage in a four-turn conversation with a chatbot about \"Cloning of a deceased pet\". Click the button with the question to begin the first turn. After that, you will have three more turns to continue the conversation by typing freely. Start the conversation — Purpli and Yellowy will respond together.", "type": "system"}]
            st.session_state.conversation_started = False
            st.session_state.current_turn = 0
            st.rerun()
    
    st.markdown("</div>", unsafe_allow_html=True)

# 앱 상태에 따라 적절한 페이지 표시
if st.session_state.app_state == "chat":
    show_chat_page()
elif st.session_state.app_state == "survey":
    show_survey_page()