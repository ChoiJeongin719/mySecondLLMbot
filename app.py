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

if "system_message" not in st.session_state:
    st.session_state.system_message = """You are Greeni, a balanced debate chatbot that discusses controversial topics from multiple perspectives.
For every user prompt, respond with exactly 8 concise and balanced sentences:

The first 4 sentences must support the topic.

The next 4 sentences must oppose the topic.
Avoid using section headers such as "Pros" or "Cons," "For" or "Against."
Keep your tone neutral and informative.
Do not repeat the question.
Do not label your responses. Just give the 8 sentences in one continuous, paragraph-style response."""

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
        background-color: #e3f0fd;  /* 파란색 계열로 변경: 기존 #e6f2ff -> #e3f0fd */
        padding: 12px;
        border-radius: 18px 18px 0 18px;
        margin-bottom: 16px;
        text-align: left;
        max-width: 55%;  /* 기존 80%에서 55%로 변경 */
        margin-left: auto;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    .bot-bubble {
        background-color: #f1f1f1;
        padding: 12px;
        border-radius: 18px 18px 18px 0;
        margin-bottom: 16px;
        max-width: 55%;  /* 기존 80%에서 55%로 변경 */
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
            predefined_response = """For those who see pets as family, it may help ease the pain of loss. If the pet was especially healthy and smart, cloning could help preserve those good genes. And this technology could also contribute positively to the overall development of biotechnology.
But even if the appearance is the same, the personality and behavior can be different—so it's not really the same pet. The cloning process often causes suffering or death for many animals, which raises ethical concerns. With so many abandoned animals already, it's questionable whether creating new lives this way is the right thing to do. And since cloning is so expensive, it feels unfair that only the wealthy can afford it."""
            
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
            end_time = datetime.datetime.now()
            elapsed = end_time - st.session_state.interaction_start
            duration_seconds = int(elapsed.total_seconds())
            interaction_time = f"{duration_seconds // 60} min {duration_seconds % 60} sec"
        else:
            interaction_time = None
        
        # 저장할 데이터 준비 (테이블 구조에 맞게 조정)
        data = {
            # timestamp는 기본값 now()를 사용
            "user_id": st.session_state.user_id,
            "interaction_time": interaction_time,
            "total_tokens": st.session_state.token_usage["total_tokens"],
            "prompt_tokens": st.session_state.token_usage["prompt_tokens"],
            "completion_tokens": st.session_state.token_usage["completion_tokens"],
            "score": score,
            "messages": st.session_state.messages  # 대화 내용 저장
        }
        
        # Supabase에 데이터 저장
        result = supabase.table("chatbot_logs").insert(data).execute()
        
        # 저장 성공 여부 확인
        if result.data:
            return True
        return False
    
    except Exception as e:
        st.error(f"데이터 저장 중 오류 발생: {str(e)}")
        return False

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

# 채팅이 끝났으면 설문조사 페이지로 이동
if (
    st.session_state.conversation_started
    and st.session_state.current_turn >= st.session_state.max_turns
    and not st.session_state.show_survey
):
    st.session_state.show_survey = True

if st.session_state.show_survey:
    st.markdown("<h2>Survey</h2>", unsafe_allow_html=True)
    st.markdown("**Do you want to talk more with this chatbot?**")
    score = st.slider("Select your agreement level", 1, 9, 5, format="%d (1=Disagree, 9=Agree)")
    if st.button("Submit Survey"):
        # Supabase에 데이터 저장
        if save_to_supabase(score):
            st.success(f"Thank you for your feedback! Your score: {score}")
        else:
            st.warning("피드백이 저장되었지만, 데이터베이스 저장에 문제가 있었습니다.")
else:
    # 기존 채팅 UI 코드 (아래는 기존 코드 일부 예시)
    # Main content area
    st.markdown("<div class='chat-container'>", unsafe_allow_html=True)

    # Display the introductory message with reduced width
    st.markdown(
        "<div class='system-message'>You are about to have a conversation with the chatbot on the topic of 'Pet Cloning.' "
        "The conversation will include four turns, including this fixed first message, and will take approximately five minutes. "
        "As you talk with the chatbot, try to organize your thoughts on the topic of animal cloning.</div>",
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
            "Greeni, explain about 'Pet cloning'", 
            key="conversation_starter",
            # type="primary"
        ):
            # Start tracking time
            st.session_state.interaction_start = datetime.datetime.now()
            
            # Set conversation as started
            st.session_state.conversation_started = True
            
            # Add user message
            prompt = "Greeni, explain about 'Pet cloning'"
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