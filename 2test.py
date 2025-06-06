import os
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import json
import glob
import datetime  # 시간 측정을 위해 추가

# Load environment variables from .env file
load_dotenv()

# Set page config
st.set_page_config(
    page_title="토론 챗봇",
    page_icon="🤖",
    layout="wide"
)

# Initialize session state variables if they don't exist
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "안녕하세요! 토론 채팅방입니다. 토론하고 싶은 주제를 입력해주세요.", "type": "system"}]

if "system_message_pro" not in st.session_state:
    st.session_state.system_message_pro = "당신은 사용자가 제시한 주제에 대해 찬성 입장을 취하는 토론자입니다. 논리적이고 설득력 있는 찬성 입장의 의견을 제시해주세요. 4문장 이내로 간결하게 반말로 답변해주세요."

if "system_message_con" not in st.session_state:
    st.session_state.system_message_con = "당신은 사용자가 제시한 주제에 대해 반대 입장을 취하는 토론자입니다. 논리적이고 설득력 있는 반대 입장의 의견을 제시해주세요. 4문장 이내로 간결하게 반말로 답변해주세요."

if "usage_stats" not in st.session_state:
    st.session_state.usage_stats = []

if "show_process" not in st.session_state:
    st.session_state.show_process = False

# 세션 시간 측정을 위한 변수들 추가
if "session_start_time" not in st.session_state:
    st.session_state.session_start_time = datetime.datetime.now()

if "last_interaction_time" not in st.session_state:
    st.session_state.last_interaction_time = datetime.datetime.now()

if "total_session_duration" not in st.session_state:
    st.session_state.total_session_duration = datetime.timedelta(0)

if "interaction_count" not in st.session_state:
    st.session_state.interaction_count = 0

# 사용 시간 기록 함수
def update_session_time():
    """현재 세션의 사용 시간을 업데이트합니다"""
    now = datetime.datetime.now()
    
    # 마지막 상호작용 이후 10분(600초) 이상 지났다면 새 세션으로 간주
    time_diff = (now - st.session_state.last_interaction_time).total_seconds()
    if time_diff > 600:  # 10분 이상 차이
        # 이전 세션 시간 저장
        session_duration = st.session_state.last_interaction_time - st.session_state.session_start_time
        st.session_state.total_session_duration += session_duration
        
        # 새 세션 시작
        st.session_state.session_start_time = now
    
    # 마지막 상호작용 시간 업데이트
    st.session_state.last_interaction_time = now
    
    # 상호작용 횟수 증가
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
    # 상호작용 시간 업데이트
    update_session_time()
    
    client = get_openai_client()
    model_name = os.getenv("GITHUB_MODEL", "openai/gpt-4o")
    
    # Prepare previous conversation history (excluding the system message)
    history = []
    for msg in st.session_state.messages:
        if msg["role"] != "system" and "type" not in msg:  # Skip system messages
            history.append(msg)
    
    # 찬성 메시지 생성
    pro_messages = [{"role": "system", "content": st.session_state.system_message_pro}] + history + [{"role": "user", "content": prompt}]
    
    # 반대 메시지 생성
    con_messages = [{"role": "system", "content": st.session_state.system_message_con}] + history + [{"role": "user", "content": prompt}]
    
    try:
        # 채팅방 형식으로 변경하여 응답 표시
        status_placeholder = st.empty()
        status_placeholder.markdown("응답 생성 중...", unsafe_allow_html=True)
        
        # 찬성 응답 생성
        full_pro_response = ""
        usage_pro = None
        
        pro_response = client.chat.completions.create(
            messages=pro_messages,
            model=model_name,
            stream=True,
            stream_options={'include_usage': True}
        )
        
        # 찬성 응답 추가
        pro_placeholder = st.empty()
        
        # 찬성 응답 스트리밍
        for chunk in pro_response:
            if chunk.choices and chunk.choices[0].delta.content:
                content_chunk = chunk.choices[0].delta.content
                full_pro_response += content_chunk
                pro_placeholder.markdown(
                    f"<div class='pro-name'>보라</div><div class='pro-bubble'>{full_pro_response}▌</div>",
                    unsafe_allow_html=True
                )
                
            if chunk.usage:
                usage_pro = chunk.usage
        
        # 최종 찬성 응답 업데이트 (커서 제거)
        pro_placeholder.markdown(
            f"<div class='pro-name'>보라</div><div class='pro-bubble'>{full_pro_response}</div>",
            unsafe_allow_html=True
        )
        
        # 반대 응답 생성
        full_con_response = ""
        usage_con = None
        
        con_response = client.chat.completions.create(
            messages=con_messages,
            model=model_name,
            stream=True,
            stream_options={'include_usage': True}
        )
        
        # 반대 응답 추가
        con_placeholder = st.empty()
        
        # 반대 응답 스트리밍
        for chunk in con_response:
            if chunk.choices and chunk.choices[0].delta.content:
                content_chunk = chunk.choices[0].delta.content
                full_con_response += content_chunk
                con_placeholder.markdown(
                    f"<div class='con-name'>노랑이</div><div class='con-bubble'>{full_con_response}▌</div>",
                    unsafe_allow_html=True
                )
                
            if chunk.usage:
                usage_con = chunk.usage
        
        # 최종 반대 응답 업데이트 (커서 제거)
        con_placeholder.markdown(
            f"<div class='con-name'>노랑이</div><div class='con-bubble'>{full_con_response}</div>",
            unsafe_allow_html=True
        )
        
        # 상태 표시 제거
        status_placeholder.empty()
        
        # 응답을 세션 상태에 추가
        st.session_state.messages.append({"role": "assistant", "content": full_pro_response, "type": "pro"})
        st.session_state.messages.append({"role": "assistant", "content": full_con_response, "type": "con"})
        
        # 사용량 통계 저장
        if usage_pro and usage_con:
            # Pydantic 처리
            usage_pro_dict = usage_pro.model_dump() if hasattr(usage_pro, 'model_dump') else usage_pro.dict()
            usage_con_dict = usage_con.model_dump() if hasattr(usage_con, 'model_dump') else usage_con.dict()
            
            st.session_state.usage_stats.append({
                "prompt_tokens": usage_pro_dict.get("prompt_tokens", 0) + usage_con_dict.get("prompt_tokens", 0),
                "completion_tokens": usage_pro_dict.get("completion_tokens", 0) + usage_con_dict.get("completion_tokens", 0),
                "total_tokens": usage_pro_dict.get("total_tokens", 0) + usage_con_dict.get("total_tokens", 0)
            })
        
        # 프로세스 표시 활성화된 경우
        if st.session_state.show_process:
            process_container = st.container()
            with process_container:
                st.markdown("### 모델 처리 과정")
                
                # 요청 상세 정보 표시
                request_expander = st.expander("요청 상세 정보", expanded=False)
                with request_expander:
                    st.markdown("**찬성 시스템 메시지:**")
                    st.code(st.session_state.system_message_pro)
                    st.markdown("**반대 시스템 메시지:**")
                    st.code(st.session_state.system_message_con)
                    st.markdown("**사용자 입력:**")
                    st.code(prompt)
                
                # 원시 응답 표시
                response_expander = st.expander("원시 응답", expanded=False)
                with response_expander:
                    st.markdown("**찬성 응답:**")
                    st.code(full_pro_response, language="markdown")
                    st.markdown("**반대 응답:**")
                    st.code(full_con_response, language="markdown")
                
                # 사용량 통계 표시
                if usage_pro and usage_con:
                    usage_expander = st.expander("사용량 통계", expanded=False)
                    with usage_expander:
                        st.markdown("**찬성 응답 사용량:**")
                        st.markdown(f"- 프롬프트 토큰: {usage_pro_dict.get('prompt_tokens', 0)}")
                        st.markdown(f"- 응답 토큰: {usage_pro_dict.get('completion_tokens', 0)}")
                        st.markdown(f"- 총 토큰: {usage_pro_dict.get('total_tokens', 0)}")
                        
                        st.markdown("**반대 응답 사용량:**")
                        st.markdown(f"- 프롬프트 토큰: {usage_con_dict.get('prompt_tokens', 0)}")
                        st.markdown(f"- 응답 토큰: {usage_con_dict.get('completion_tokens', 0)}")
                        st.markdown(f"- 총 토큰: {usage_con_dict.get('total_tokens', 0)}")
        
        return True
    except Exception as e:
        st.error(f"응답 생성 중 오류 발생: {str(e)}")
        return False

# CSS 스타일 정의 수정
st.markdown("""
    <style>
    .pro-bubble {
        background-color: #f1f1f1;
        padding: 12px;
        border-radius: 18px 18px 18px 0;
        margin-bottom: 16px;
        max-width: 68%;  /* 수정된 크기 유지 */
        position: relative;
        margin-left: 50px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }

    .pro-bubble::before {
        content: "";
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background-color: #9370DB;  /* 보라색 */
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
        background-color: #f1f1f1;
        padding: 12px;
        border-radius: 18px 18px 18px 0;
        margin-bottom: 16px;
        max-width: 68%;  /* 동일하게 68%로 맞춤 */
        position: relative;
        margin-left: 50px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }

    .con-bubble::before {
        content: "";
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background-color: #FFD700;  /* 노랑색 */
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
        background-color: #e6f2ff;
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
        width: calc(100% - 250px) !important; /* 사이드바 너비 조정 */
        background-color: white !important;
        z-index: 1000 !important;
    }

    .main-content {
        padding-bottom: 100px; /* 고정 입력창을 위한 하단 여백 */
    }

    .pro-name {
        font-size: 0.8em;
        color: #9370DB;  /* 보라색 */
        font-weight: bold;
        margin-bottom: 4px;
        margin-left: 0px;
    }

    .con-name {
        font-size: 0.8em;
        color: #FFD700;  /* 노랑색으로 변경 */
        font-weight: bold;
        margin-bottom: 4px;
        margin-left: 0px;
    }
    </style>
""", unsafe_allow_html=True)

# UI Layout
st.title("🤖 토론 챗봇")

# 사이드바 설정
with st.sidebar:
    st.subheader("설정")
    
    # 시간 측정 통계 표시
    with st.expander("사용 시간 통계", expanded=False):
        # 현재 세션 계산
        current_session_duration = st.session_state.last_interaction_time - st.session_state.session_start_time
        total_time = st.session_state.total_session_duration + current_session_duration
        
        # 시간 형식 지정 (시:분:초)
        def format_timedelta(td):
            total_seconds = int(td.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        st.write("### 사용 시간")
        st.write(f"현재 세션: {format_timedelta(current_session_duration)}")
        st.write(f"총 사용 시간: {format_timedelta(total_time)}")
        st.write(f"총 상호작용 횟수: {st.session_state.interaction_count}")
        st.write(f"첫 사용 시간: {st.session_state.session_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        st.write(f"마지막 사용 시간: {st.session_state.last_interaction_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 찬성 시스템 메시지 수정
    st.text_area(
        "찬성 챗봇 설정", 
        value=st.session_state.system_message_pro,
        key="system_message_pro_input",
        height=150
    )
    
    # 반대 시스템 메시지 수정
    st.text_area(
        "반대 챗봇 설정", 
        value=st.session_state.system_message_con,
        key="system_message_con_input",
        height=150
    )
    
    if st.button("시스템 메시지 업데이트"):
        st.session_state.system_message_pro = st.session_state.system_message_pro_input
        st.session_state.system_message_con = st.session_state.system_message_con_input
        st.success("시스템 메시지가 업데이트되었습니다!")
    
    # 기타 사이드바 요소
    st.markdown("---")
    
    # 채팅 기록 보기
    with st.expander("채팅 기록 보기"):
        st.json(st.session_state.messages)
    
    # 사용량 통계 보기
    with st.expander("사용량 통계 보기"):
        if st.session_state.usage_stats:
            for i, usage in enumerate(st.session_state.usage_stats):
                st.write(f"메시지 {i+1}:")
                st.write(f"- 프롬프트 토큰: {usage['prompt_tokens']}")
                st.write(f"- 응답 토큰: {usage['completion_tokens']}")
                st.write(f"- 총 토큰: {usage['total_tokens']}")
                st.divider()
            
            # 총 사용량 계산
            total_prompt = sum(u["prompt_tokens"] for u in st.session_state.usage_stats)
            total_completion = sum(u["completion_tokens"] for u in st.session_state.usage_stats)
            total = sum(u["total_tokens"] for u in st.session_state.usage_stats)
            
            st.write("### 총 사용량")
            st.write(f"- 총 프롬프트 토큰: {total_prompt}")
            st.write(f"- 총 응답 토큰: {total_completion}")
            st.write(f"- 총 토큰: {total}")
        else:
            st.write("아직 사용량 데이터가 없습니다.")
    
    # 채팅 초기화 버튼
    if st.button("채팅 초기화"):
        st.session_state.messages = [{"role": "assistant", "content": "안녕하세요! 토론 채팅방입니다. 토론하고 싶은 주제를 입력해주세요.", "type": "system"}]
        st.session_state.usage_stats = []
        
        # 시간 관련 변수도 초기화
        now = datetime.datetime.now()
        st.session_state.session_start_time = now
        st.session_state.last_interaction_time = now
        st.session_state.total_session_duration = datetime.timedelta(0)
        st.session_state.interaction_count = 0
        
        st.success("채팅 기록이 초기화되었습니다!")
    
    # 프로세스 표시 토글
    st.markdown("---")
    st.session_state.show_process = st.checkbox("모델 처리 과정 보기", value=st.session_state.show_process)

# 메인 채팅 영역
chat_container = st.container()
with chat_container:
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    
    # 채팅 기록을 순서대로 처리
    i = 0
    while i < len(st.session_state.messages):
        message = st.session_state.messages[i]
        
        if message["role"] == "user":
            # 사용자 메시지
            st.markdown(
                f"<div class='user-bubble'>{message['content']}</div>",
                unsafe_allow_html=True
            )
            i += 1
        elif message["role"] == "assistant" and "type" in message and message["type"] == "system":
            # 시스템 메시지
            st.markdown(
                f"<div class='system-bubble'>{message['content']}</div>",
                unsafe_allow_html=True
            )
            i += 1
        elif message["role"] == "assistant" and "type" in message and message["type"] == "pro":
            # 찬성 메시지 - 보라색 프로필로 표시하고 이름을 "보라"로 변경
            st.markdown(
                f"<div class='pro-name'>보라</div><div class='pro-bubble'>{message['content']}</div>",
                unsafe_allow_html=True
            )
            i += 1
        elif message["role"] == "assistant" and "type" in message and message["type"] == "con":
            # 반대 메시지 - 노랑색 프로필로 표시하고 이름을 "노랑이"로 변경
            st.markdown(
                f"<div class='con-name'>노랑이</div><div class='con-bubble'>{message['content']}</div>",
                unsafe_allow_html=True
            )
            i += 1
        else:
            # 기타 메시지
            st.markdown(
                f"<div class='system-bubble'>{message['content']}</div>",
                unsafe_allow_html=True
            )
            i += 1
    
    st.markdown('</div>', unsafe_allow_html=True)

# 채팅 입력
if prompt := st.chat_input("토론하고 싶은 주제를 입력하세요..."):
    # 사용자 메시지 표시 - 챗봇 아이콘 없이 표시
    st.markdown(
        f"<div class='user-bubble'>{prompt}</div>",
        unsafe_allow_html=True
    )
    
    # 사용자 메시지를 기록에 추가
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # 찬성/반대 응답 생성 및 표시
    generate_debate_responses(prompt)

