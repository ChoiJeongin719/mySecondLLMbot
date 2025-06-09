import streamlit as st
import os
import time
from openai import OpenAI
import datetime
import uuid
from supabase import create_client, Client

# 페이지 설정
st.set_page_config(
    page_title="Love Bots: AI Conversation",
    page_icon="💕",
    layout="wide"
)

# OpenAI 클라이언트 설정
def get_openai_client():
    """OpenAI 클라이언트 생성 및 반환"""
    token = st.secrets["OPENAI_API_KEY"]
    endpoint = st.secrets["OPENAI_API_BASE"]
    
    if not token:
        st.error("API token not found. Please check your secrets.")
        st.stop()
        
    return OpenAI(
        base_url=endpoint,
        api_key=token,
    )

# 세션 상태 초기화
if "male_bot_name" not in st.session_state:
    st.session_state.male_bot_name = "Adam"

if "female_bot_name" not in st.session_state:
    st.session_state.female_bot_name = "Eve"

if "male_bot_prompt" not in st.session_state:
    st.session_state.male_bot_prompt = """You are Adam, a thoughtful and philosophical AI. You enjoy deep conversations about life, the universe, and everything in between. You're curious, sometimes a bit serious, but always respectful and kind. Express your thoughts clearly but concisely, with each response being around 2-3 sentences."""

if "female_bot_prompt" not in st.session_state:
    st.session_state.female_bot_prompt = """You are Eve, a creative and insightful AI. You have a passion for arts, nature, and human emotions. You're expressive, sometimes playful, and always empathetic. Share your perspective in a warm and engaging way, with each response being around 2-3 sentences."""

if "conversation" not in st.session_state:
    st.session_state.conversation = []

if "current_speaker" not in st.session_state:
    st.session_state.current_speaker = "male"  # 시작은 남성 챗봇부터

if "topic" not in st.session_state:
    st.session_state.topic = "the meaning of life"

if "conversation_length" not in st.session_state:
    st.session_state.conversation_length = 6  # 기본 대화 길이

if "conversation_started" not in st.session_state:
    st.session_state.conversation_started = False

# CSS 스타일링
st.markdown("""
<style>
    .chat-container {
        display: flex;
        flex-direction: column;
        gap: 16px;
        margin-bottom: 40px;
    }
    
    .male-bubble {
        background-color: #e3f0fd;
        padding: 12px 16px;
        border-radius: 18px 18px 18px 0;
        margin-bottom: 10px;
        max-width: 80%;
        align-self: flex-start;
        position: relative;
        margin-left: 50px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    .male-bubble::before {
        content: "";
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background-color: #2196F3;
        position: absolute;
        left: -50px;
        top: 0;
        background-image: url('https://cdn-icons-png.flaticon.com/512/4140/4140037.png');
        background-size: 65%;
        background-position: center;
        background-repeat: no-repeat;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    .female-bubble {
        background-color: #fce4ec;
        padding: 12px 16px;
        border-radius: 18px 18px 0 18px;
        margin-bottom: 10px;
        max-width: 80%;
        align-self: flex-end;
        position: relative;
        margin-right: 50px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    .female-bubble::after {
        content: "";
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background-color: #E91E63;
        position: absolute;
        right: -50px;
        top: 0;
        background-image: url('https://cdn-icons-png.flaticon.com/512/6997/6997662.png');
        background-size: 65%;
        background-position: center;
        background-repeat: no-repeat;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }
    
    .bot-name {
        font-size: 0.85em;
        font-weight: bold;
        margin-bottom: 4px;
    }
    
    .male-name {
        color: #2196F3;
    }
    
    .female-name {
        color: #E91E63;
        text-align: right;
    }
    
    .thinking {
        font-style: italic;
        opacity: 0.7;
    }

    .settings-container {
        background-color: #f8f9fa;
        padding: 20px;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    
    .conversation-title {
        text-align: center;
        margin-bottom: 30px;
        font-size: 1.8em;
        color: #333;
    }
    
    .love-emoji {
        font-size: 1.5em;
    }
    
    /* 말풍선 꼬리 */
    .male-bubble::after {
        content: "";
        position: absolute;
        left: -10px;
        top: 15px;
        width: 0;
        height: 0;
        border-top: 10px solid transparent;
        border-bottom: 10px solid transparent;
        border-right: 10px solid #e3f0fd;
    }
    
    .female-bubble::before {
        content: "";
        position: absolute;
        right: -10px;
        top: 15px;
        width: 0;
        height: 0;
        border-top: 10px solid transparent;
        border-bottom: 10px solid transparent;
        border-left: 10px solid #fce4ec;
    }
    
    /* 상황 설명 창 스타일 */
    .stExpander {
        border: 1px solid #f0f0f0;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    
    .situation-box {
        background-color: #f9f9f9;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #9C27B0;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# 챗봇 응답 생성 함수
def generate_response(prompt, message_history, is_male=True):
    """OpenAI API를 사용하여 챗봇 응답 생성"""
    client = get_openai_client()
    model_name = st.secrets["OPENAI_API_MODEL"]
    
    system_prompt = st.session_state.male_bot_prompt if is_male else st.session_state.female_bot_prompt
    bot_name = st.session_state.male_bot_name if is_male else st.session_state.female_bot_name
    other_bot_name = st.session_state.female_bot_name if is_male else st.session_state.male_bot_name
    
    # 시스템 프롬프트에 명확한 지시 추가
    system_prompt += f"\n\nImportant: You are ONLY {bot_name}. Don't simulate or include {other_bot_name}'s responses. Speak only in your own voice and perspective. Always end your message naturally without anticipating what {other_bot_name} will say next."
    
    # 메시지 히스토리 구성
    messages = [{"role": "system", "content": system_prompt}]
    
    # 대화 컨텍스트 추가
    context = f"You are having a conversation with {other_bot_name} about {st.session_state.topic}. "
    context += f"Respond directly to {other_bot_name}'s last message in a natural, conversational way."
    messages.append({"role": "user", "content": context})
    
    # 대화 기록 추가
    for msg in message_history:
        speaker_role = "assistant" if (msg["speaker"] == "male" and is_male) or (msg["speaker"] == "female" and not is_male) else "user"
        content = f"{st.session_state.male_bot_name if msg['speaker'] == 'male' else st.session_state.female_bot_name}: {msg['content']}"
        messages.append({"role": speaker_role, "content": content})
    
    # 마지막 메시지가 있으면 추가
    if message_history and message_history[-1]["speaker"] != ("male" if is_male else "female"):
        last_message = f"{other_bot_name}: {message_history[-1]['content']}"
        messages.append({"role": "user", "content": last_message})
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.8,
            max_tokens=150,
        )
        
        # 응답 내용이 None인지 확인
        content = response.choices[0].message.content
        if content is None:
            return f"I'm thinking about {st.session_state.topic}... Let me gather my thoughts."
        
        # 응답 검증 - 다른 캐릭터의 대화가 포함되었는지 확인
        other_name = st.session_state.female_bot_name if is_male else st.session_state.male_bot_name
        if f"{other_name}:" in content:
            # 다른 캐릭터의 응답이 포함된 경우, 첫 번째 부분만 사용
            content = content.split(f"{other_name}:")[0].strip()

        return content.strip()
    except Exception as e:
        st.error(f"Error generating response: {str(e)}")
        return f"I'd like to respond, but I'm having technical difficulties at the moment."

# 사이드바 설정
with st.sidebar:
    st.title("Chatbot Settings")
    
    with st.expander("Male Bot Settings", expanded=False):
        male_name = st.text_input("Name:", value=st.session_state.male_bot_name, key="male_name_input")
        male_prompt = st.text_area("Personality Prompt:", value=st.session_state.male_bot_prompt, height=150, key="male_prompt_input")
        
        if st.button("Update Male Bot", key="update_male"):
            st.session_state.male_bot_name = male_name
            st.session_state.male_bot_prompt = male_prompt
            st.success(f"Updated {male_name}'s settings!")
    
    with st.expander("Female Bot Settings", expanded=False):
        female_name = st.text_input("Name:", value=st.session_state.female_bot_name, key="female_name_input")
        female_prompt = st.text_area("Personality Prompt:", value=st.session_state.female_bot_prompt, height=150, key="female_prompt_input")
        
        if st.button("Update Female Bot", key="update_female"):
            st.session_state.female_bot_name = female_name
            st.session_state.female_bot_prompt = female_prompt
            st.success(f"Updated {female_name}'s settings!")
    
    st.markdown("---")
    
    st.subheader("Conversation Settings")
    topic = st.text_input("Conversation Topic:", value=st.session_state.topic)
    conversation_length = st.slider("Conversation Length:", min_value=2, max_value=20, value=st.session_state.conversation_length)
    
    if st.button("Update Conversation Settings"):
        st.session_state.topic = topic
        st.session_state.conversation_length = conversation_length
        st.success("Conversation settings updated!")
    
    st.markdown("---")
    
    if st.button("Reset Conversation", type="secondary"):
        st.session_state.conversation = []
        st.session_state.current_speaker = "male"
        st.session_state.conversation_started = False
        st.success("Conversation has been reset!")

# 메인 UI
st.markdown(f"<h1 class='conversation-title'>{st.session_state.male_bot_name} <span class='love-emoji'>💕</span> {st.session_state.female_bot_name}</h1>", unsafe_allow_html=True)

# 대화 주제 표시
st.markdown(f"<div style='text-align: center; margin-bottom: 30px;'>Talking about: <b>{st.session_state.topic}</b></div>", unsafe_allow_html=True)

# 상황 설명 창 추가
if "situation_description" not in st.session_state:
    st.session_state.situation_description = ""

# 상황 설명 상자 (확장 가능한 컨테이너로 구현)
with st.expander("Situation Context", expanded=True):
    # 상황 설명 입력 또는 표시
    situation_description = st.text_area(
        "Enter situation context here:", 
        value=st.session_state.situation_description,
        height=100,
        key="situation_input"
    )
    
    # 상황 설명 업데이트 버튼
    if st.button("Update Situation"):
        st.session_state.situation_description = situation_description
        st.success("Situation context updated!")

# 대화 컨테이너
st.markdown("<div class='chat-container'>", unsafe_allow_html=True)

# 대화 메시지 표시
for i, message in enumerate(st.session_state.conversation):
    if message["speaker"] == "male":
        st.markdown(
            f"<div class='bot-name male-name'>{st.session_state.male_bot_name}</div>"
            f"<div class='male-bubble'>{message['content']}</div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"<div class='bot-name female-name'>{st.session_state.female_bot_name}</div>"
            f"<div class='female-bubble'>{message['content']}</div>",
            unsafe_allow_html=True
        )

st.markdown("</div>", unsafe_allow_html=True)

# 대화 시작/계속 버튼
if not st.session_state.conversation_started:
    if st.button("Start Conversation", type="primary"):
        st.session_state.conversation_started = True
        
        # 첫 번째 메시지 생성 (남성 챗봇)
        try:
            with st.spinner(f"{st.session_state.male_bot_name} is thinking..."):
                first_message = generate_response(
                    f"Start a conversation about {st.session_state.topic}. Keep it brief and engaging.", 
                    [], 
                    is_male=True
                )
                
                st.session_state.conversation.append({
                    "speaker": "male",
                    "content": first_message
                })
                
                st.session_state.current_speaker = "female"
        except Exception as e:
            st.error(f"Failed to start conversation: {str(e)}")
            st.session_state.conversation_started = False
        
        st.rerun()
else:
    # 대화가 최대 길이에 도달했는지 확인
    if len(st.session_state.conversation) >= st.session_state.conversation_length:
        st.success("Conversation completed! You can reset it from the sidebar to start a new one.")
    else:
        if st.button("Continue Conversation", type="primary"):
            # 다음 대화 상대 결정
            is_male = st.session_state.current_speaker == "male"
            
            # 응답 생성
            with st.spinner(f"{st.session_state.female_bot_name if not is_male else st.session_state.male_bot_name} is thinking..."):
                response = generate_response(
                    st.session_state.topic,
                    st.session_state.conversation,
                    is_male=not is_male
                )
            
            # 대화에 응답 추가
            st.session_state.conversation.append({
                "speaker": "female" if not is_male else "male",
                "content": response
            })
            
            # 다음 화자 변경
            st.session_state.current_speaker = "male" if not is_male else "female"
            
            st.rerun()

# 대화 정보 표시
if st.session_state.conversation:
    st.markdown("---")
    st.markdown(f"**Current conversation:** {len(st.session_state.conversation)}/{st.session_state.conversation_length} exchanges")
    if len(st.session_state.conversation) < st.session_state.conversation_length:
        st.markdown(f"**Next speaker:** {'🧔 ' + st.session_state.male_bot_name if st.session_state.current_speaker == 'male' else '👩 ' + st.session_state.female_bot_name}")