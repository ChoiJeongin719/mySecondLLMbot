import os
import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import json
import glob
import threading

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
    st.session_state.system_message_pro = "당신은 사용자가 제시한 주제에 대해 찬성 입장을 취하는 토론자입니다. 논리적이고 설득력 있는 찬성 입장의 의견을 제시해주세요."

if "system_message_con" not in st.session_state:
    st.session_state.system_message_con = "당신은 사용자가 제시한 주제에 대해 반대 입장을 취하는 토론자입니다. 논리적이고 설득력 있는 반대 입장의 의견을 제시해주세요."

if "usage_stats" not in st.session_state:
    st.session_state.usage_stats = []

if "show_process" not in st.session_state:
    st.session_state.show_process = False

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
    """Generate two separate responses - one pro, one con simultaneously"""
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
        # 2열 레이아웃 생성 (더 넓은 간격으로 조정)
        cols = st.columns([1, 0.2, 1])  # 왼쪽 칼럼, 간격, 오른쪽 칼럼
        
        # 찬성 응답 컨테이너 및 플레이스홀더 설정 (왼쪽 칼럼)
        with cols[0]:
            st.markdown("<h4 style='text-align: center;'>찬성 의견</h4>", unsafe_allow_html=True)
            pro_placeholder = st.empty()
        
        # 반대 응답 컨테이너 및 플레이스홀더 설정 (오른쪽 칼럼)
        with cols[2]:
            st.markdown("<h4 style='text-align: center;'>반대 의견</h4>", unsafe_allow_html=True)
            con_placeholder = st.empty()
        
        # 결과를 저장할 변수
        full_pro_response = ""
        full_con_response = ""
        usage_pro = None
        usage_con = None
        
        # 스레드 완료 플래그
        pro_completed = threading.Event()
        con_completed = threading.Event()
        
        # 찬성 응답 생성 함수
        def generate_pro_response():
            nonlocal full_pro_response, usage_pro
            
            pro_response = client.chat.completions.create(
                messages=pro_messages,
                model=model_name,
                stream=True,
                stream_options={'include_usage': True}
            )
            
            # 찬성 응답 스트리밍
            for chunk in pro_response:
                if chunk.choices and chunk.choices[0].delta.content:
                    content_chunk = chunk.choices[0].delta.content
                    full_pro_response += content_chunk
                    pro_placeholder.markdown(
                        f"<div style='background-color: #90EE90; padding: 10px; border-radius: 5px;'>{full_pro_response}▌</div>",
                        unsafe_allow_html=True
                    )
                        
                if chunk.usage:
                    usage_pro = chunk.usage
            
            # 최종 찬성 응답 업데이트 (커서 제거)
            pro_placeholder.markdown(
                f"<div style='background-color: #90EE90; padding: 10px; border-radius: 5px;'>{full_pro_response}</div>",
                unsafe_allow_html=True
            )
            
            # 완료 표시
            pro_completed.set()
        
        # 반대 응답 생성 함수
        def generate_con_response():
            nonlocal full_con_response, usage_con
            
            con_response = client.chat.completions.create(
                messages=con_messages,
                model=model_name,
                stream=True,
                stream_options={'include_usage': True}
            )
            
            # 반대 응답 스트리밍
            for chunk in con_response:
                if chunk.choices and chunk.choices[0].delta.content:
                    content_chunk = chunk.choices[0].delta.content
                    full_con_response += content_chunk
                    con_placeholder.markdown(
                        f"<div style='background-color: #FFB6C1; padding: 10px; border-radius: 5px;'>{full_con_response}▌</div>",
                        unsafe_allow_html=True
                    )
                        
                if chunk.usage:
                    usage_con = chunk.usage
            
            # 최종 반대 응답 업데이트 (커서 제거)
            con_placeholder.markdown(
                f"<div style='background-color: #FFB6C1; padding: 10px; border-radius: 5px;'>{full_con_response}</div>",
                unsafe_allow_html=True
            )
            
            # 완료 표시
            con_completed.set()
        
        # 두 스레드 생성 및 시작
        pro_thread = threading.Thread(target=generate_pro_response)
        con_thread = threading.Thread(target=generate_con_response)
        
        pro_thread.start()
        con_thread.start()
        
        # 두 스레드가 모두 완료될 때까지 대기
        pro_completed.wait()
        con_completed.wait()
        
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

# CSS 스타일 정의 추가
st.markdown("""
    <style>
    .pro-bubble {
        background-color: #90EE90;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
        max-width: 95%;  /* 버블 너비 제한 */
        margin-left: auto;
        margin-right: auto;
    }
    .con-bubble {
        background-color: #FFB6C1;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
        max-width: 95%;  /* 버블 너비 제한 */
        margin-left: auto;
        margin-right: auto;
    }
    .user-bubble {
        background-color: #F0F2F6;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
        text-align: right;
        max-width: 50%;
        margin-left: auto;
    }
    .system-bubble {
        background-color: #E8E8E8;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
        max-width: 50%;
        margin-left: auto;
        margin-right: auto;
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
    .debate-container {
        display: flex;
        justify-content: space-between;
        gap: 20px;
        margin-bottom: 15px;
    }
    .debate-column {
        flex: 1;
        max-width: 48%;
    }
    </style>
""", unsafe_allow_html=True)

# UI Layout
st.title("🤖 토론 챗봇")

# 사이드바 설정
with st.sidebar:
    st.subheader("설정")
    
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
        st.success("채팅 기록이 초기화되었습니다!")
    
    # 프로세스 표시 토글
    st.markdown("---")
    st.session_state.show_process = st.checkbox("모델 처리 과정 보기", value=st.session_state.show_process)
    
# 메인 채팅 영역
chat_container = st.container()
with chat_container:
    st.markdown('<div class="main-content">', unsafe_allow_html=True)
    
    # 채팅 기록을 순서대로 처리하면서 사용자와 시스템 메시지는 전체 너비로, 찬성/반대는 2열로 표시
    i = 0
    while i < len(st.session_state.messages):
        message = st.session_state.messages[i]
        
        if message["role"] == "user":
            # 사용자 메시지 - 전체 너비로 표시
            st.markdown(
                f"<div class='user-bubble'>{message['content']}</div>",
                unsafe_allow_html=True
            )
            i += 1
        elif message["role"] == "assistant" and "type" in message and message["type"] == "system":
            # 시스템 메시지 - 전체 너비로 표시
            st.markdown(
                f"<div class='system-bubble'>{message['content']}</div>",
                unsafe_allow_html=True
            )
            i += 1
        elif message["role"] == "assistant" and "type" in message and message["type"] == "pro":
            # 찬성 메시지가 있으면 다음 메시지가 반대 메시지인지 확인
            pro_content = message["content"]
            con_content = ""
            
            # 다음 메시지가 반대 메시지인지 확인
            if i + 1 < len(st.session_state.messages) and st.session_state.messages[i + 1]["role"] == "assistant" and "type" in st.session_state.messages[i + 1] and st.session_state.messages[i + 1]["type"] == "con":
                con_content = st.session_state.messages[i + 1]["content"]
                i += 2  # 두 메시지를 모두 처리했으므로 인덱스를 2 증가
            else:
                i += 1  # 반대 메시지가 없으면 인덱스를 1만 증가
            
            # 2열 레이아웃 생성 (더 넓은 간격으로 조정)
            cols = st.columns([1, 0.2, 1])  # 왼쪽 칼럼, 간격, 오른쪽 칼럼
            
            # 찬성 의견 (왼쪽 칼럼)
            with cols[0]:
                st.markdown(
                    f"<div class='pro-bubble'>{pro_content}</div>",
                    unsafe_allow_html=True
                )
            
            # 반대 의견이 있으면 오른쪽 칼럼에 표시
            if con_content:
                with cols[2]:
                    st.markdown(
                        f"<div class='con-bubble'>{con_content}</div>",
                        unsafe_allow_html=True
                    )
        elif message["role"] == "assistant" and "type" in message and message["type"] == "con":
            # 이미 처리된 경우 스킵 (위의 pro 처리 과정에서 함께 처리됨)
            # 독립적인 con 메시지만 처리
            cols = st.columns([1, 0.2, 1])
            with cols[2]:
                st.markdown(
                    f"<div class='con-bubble'>{message['content']}</div>",
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
    # 사용자 메시지 표시
    st.markdown(
        f"<div class='user-bubble'>{prompt}</div>",
        unsafe_allow_html=True
    )
    
    # 사용자 메시지를 기록에 추가
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # 찬성/반대 응답 생성 및 표시
    generate_debate_responses(prompt)