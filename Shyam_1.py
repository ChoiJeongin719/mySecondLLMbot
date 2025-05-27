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
    page_title="챗봇",
    page_icon="🤖",
    layout="wide"
)

# Initialize session state variables if they don't exist
if "messages" not in st.session_state:
    st.session_state.messages = []  # 안내 문구 제거

if "system_message" not in st.session_state:
    st.session_state.system_message = "당신은 사용자와 대화하는 친절한 챗봇입니다. 논리적이고 도움이 되는 대답을 해주세요. 간결하게 반말로 답변해주세요. 찬성의견 4문장을 말하고 다음 문단에서는 반대 의견 4문장을 말하세요. 찬성, 반대라고 라벨링하지 마세요."

if "usage_stats" not in st.session_state:
    st.session_state.usage_stats = []

if "show_process" not in st.session_state:
    st.session_state.show_process = False

# 대화 턴 제한을 위한 변수 추가
if "max_turns" not in st.session_state:
    st.session_state.max_turns = 10

if "turn_count" not in st.session_state:
    st.session_state.turn_count = 0

if "chat_completed" not in st.session_state:
    st.session_state.chat_completed = False

# 대화 스타터 사용 여부 추적
if "starter_selected" not in st.session_state:
    st.session_state.starter_selected = False

# 시작 토픽 저장을 위한 변수
if "start_with_topic" not in st.session_state:
    st.session_state.start_with_topic = None

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

def generate_response(prompt):
    """Generate a response to the user's prompt"""
    # 대화 턴 제한 확인
    if st.session_state.turn_count >= st.session_state.max_turns:
        st.warning("대화 턴 제한에 도달했습니다. 채팅을 초기화하고 다시 시작해주세요.")
        return False
        
    # 상호작용 시간 업데이트
    update_session_time()
    
    # 턴 수 증가
    st.session_state.turn_count += 1
    
    client = get_openai_client()
    model_name = os.getenv("GITHUB_MODEL", "openai/gpt-4o")
    
    # Prepare previous conversation history (excluding the system message)
    history = []
    for msg in st.session_state.messages:
        if msg["role"] != "system" and "type" not in msg:  # Skip system messages
            history.append(msg)
    
    # 메시지 생성
    messages = [{"role": "system", "content": st.session_state.system_message}] + history + [{"role": "user", "content": prompt}]
    
    try:
        # 채팅방 형식으로 변경하여 응답 표시
        status_placeholder = st.empty()
        status_placeholder.markdown("응답 생성 중...", unsafe_allow_html=True)
        
        # 응답 생성
        full_response = ""
        usage_data = None
        
        response = client.chat.completions.create(
            messages=messages,
            model=model_name,
            stream=True,
            stream_options={'include_usage': True}
        )
        
        # 응답 추가
        response_placeholder = st.empty()
        
        # 응답 스트리밍
        for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                content_chunk = chunk.choices[0].delta.content
                full_response += content_chunk
                response_placeholder.markdown(
                    f"<div class='bot-name'>초록이</div><div class='bot-bubble'>{full_response}▌</div>",
                    unsafe_allow_html=True
                )
                
            if chunk.usage:
                usage_data = chunk.usage
        
        # 최종 응답 업데이트 (커서 제거)
        response_placeholder.markdown(
            f"<div class='bot-name'>초록이</div><div class='bot-bubble'>{full_response}</div>",
            unsafe_allow_html=True
        )
        
        # 상태 표시 제거
        status_placeholder.empty()
        
        # 응답을 세션 상태에 추가
        st.session_state.messages.append({"role": "assistant", "content": full_response, "type": "bot"})
        
        # 사용량 통계 저장
        if usage_data:
            # Pydantic 처리
            usage_dict = usage_data.model_dump() if hasattr(usage_data, 'model_dump') else usage_data.dict()
            
            st.session_state.usage_stats.append({
                "prompt_tokens": usage_dict.get("prompt_tokens", 0),
                "completion_tokens": usage_dict.get("completion_tokens", 0),
                "total_tokens": usage_dict.get("total_tokens", 0)
            })
        
        # 프로세스 표시 활성화된 경우
        if st.session_state.show_process:
            process_container = st.container()
            with process_container:
                st.markdown("### 모델 처리 과정")
                
                # 요청 상세 정보 표시
                request_expander = st.expander("요청 상세 정보", expanded=False)
                with request_expander:
                    st.markdown("**시스템 메시지:**")
                    st.code(st.session_state.system_message)
                    st.markdown("**사용자 입력:**")
                    st.code(prompt)
                
                # 원시 응답 표시
                response_expander = st.expander("원시 응답", expanded=False)
                with response_expander:
                    st.markdown("**응답:**")
                    st.code(full_response, language="markdown")
                
                # 사용량 통계 표시
                if usage_data:
                    usage_expander = st.expander("사용량 통계", expanded=False)
                    with usage_expander:
                        st.markdown("**응답 사용량:**")
                        st.markdown(f"- 프롬프트 토큰: {usage_dict.get('prompt_tokens', 0)}")
                        st.markdown(f"- 응답 토큰: {usage_dict.get('completion_tokens', 0)}")
                        st.markdown(f"- 총 토큰: {usage_dict.get('total_tokens', 0)}")
        
        # 최대 턴수 도달시 채팅 완료 설정
        if st.session_state.turn_count >= st.session_state.max_turns:
            st.session_state.chat_completed = True
        
        return True
    except Exception as e:
        st.error(f"응답 생성 중 오류 발생: {str(e)}")
        return False

# CSS 스타일 정의 수정
st.markdown("""
    <style>
    .bot-bubble {
        background-color: #f1f1f1;
        padding: 12px;
        border-radius: 18px 18px 18px 0;
        margin-bottom: 16px;
        max-width: 45%;
        position: relative;
        margin-left: 50px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }

    .bot-bubble::before {
        content: "";
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background-color: #4CAF50;  /* 초록색 */
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
        max-width: 45%;
        margin-left: auto;
        box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    }

    .system-bubble {
        background-color: #f8f9fa;
        padding: 12px;
        border-radius: 18px;
        margin-bottom: 16px;
        max-width: 45%;
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

    .bot-name {
        font-size: 0.8em;
        color: #4CAF50;  /* 초록색 */
        font-weight: bold;
        margin-bottom: 4px;
        margin-left: 0px;
    }
    </style>
""", unsafe_allow_html=True)

# UI Layout
st.title("🤖 챗봇")

# 사이드바 설정
with st.sidebar:
    st.subheader("설정")
    
    # 최대 턴 수 설정
    st.markdown("---")
    st.subheader("대화 설정")
    
    # 채팅이 완료되지 않은 경우에만 턴 수 설정 가능
    if not st.session_state.chat_completed:
        new_max_turns = st.slider(
            "최대 턴 수", 
            min_value=1, 
            max_value=10, 
            value=st.session_state.max_turns
        )
        if new_max_turns != st.session_state.max_turns:
            st.session_state.max_turns = new_max_turns
            st.success(f"최대 턴 수가 {new_max_turns}로 설정되었습니다.")
    else:
        st.info(f"현재 설정된 최대 턴 수: {st.session_state.max_turns} (채팅 초기화 후 변경 가능)")
    
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
    
    # 시스템 메시지 수정
    st.text_area(
        "챗봇 설정", 
        value=st.session_state.system_message,
        key="system_message_input",
        height=150
    )
    
    if st.button("시스템 메시지 업데이트"):
        st.session_state.system_message = st.session_state.system_message_input
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
        st.session_state.messages = []
        st.session_state.usage_stats = []
        
        # 대화 스타터 초기화
        st.session_state.starter_selected = False
        
        # 턴 수 초기화
        st.session_state.turn_count = 0
        st.session_state.chat_completed = False
        
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
    
    # 대화 스타터 표시 (처음 방문하고 아직 선택하지 않았을 때만)
    if len(st.session_state.messages) == 0 and not st.session_state.starter_selected:
        st.markdown("""
        <div style='text-align: center; margin: 50px 0 30px 0;'>
            <h3>아래 버튼을 클릭하여 대화를 시작해보세요</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # 중앙에 버튼 배치
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            starter_topic = "동물 안락사에 대해 설명해줘"
            if st.button("동물 안락사가 뭐야?", key="starter_btn", use_container_width=True):
                # 먼저 스타터 토픽 선택 상태를 변경
                st.session_state.starter_selected = True
                
                # 다음 페이지 로드에서 대화를 시작하도록 세션 상태 설정
                st.session_state.start_with_topic = starter_topic
                st.rerun()
    
    # 기존 채팅 기록 처리 코드
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
        elif message["role"] == "assistant" and "type" in message and message["type"] == "bot":
            # 챗봇 메시지 - 초록색 프로필로 표시
            st.markdown(
                f"<div class='bot-name'>초록이</div><div class='bot-bubble'>{message['content']}</div>",
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
    
    # 남은 턴 수 표시
    if not st.session_state.chat_completed:
        remaining_turns = st.session_state.max_turns - st.session_state.turn_count
        st.info(f"남은 턴 수: {remaining_turns}")
    else:
        st.success("대화가 완료되었습니다. 채팅을 초기화하려면 사이드바의 '채팅 초기화' 버튼을 클릭하세요.")

# 채팅 입력 (조건부로 활성화)
if not st.session_state.chat_completed:
    if prompt := st.chat_input("대화하고 싶은 주제를 입력하세요..."):
        # 사용자 메시지 표시 - 챗봇 아이콘 없이 표시
        st.markdown(
            f"<div class='user-bubble'>{prompt}</div>",
            unsafe_allow_html=True
        )
        
        # 사용자 메시지를 기록에 추가
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # 응답 생성 및 표시
        generate_response(prompt)
        
        # 최대 턴 수 도달 체크
        if st.session_state.turn_count >= st.session_state.max_turns:
            # 페이지 리로드하여 입력창 비활성화 및 완료 메시지 표시
            st.rerun()
else:
    # 채팅 종료 상태일 때 입력창 대신 메시지 표시
    st.markdown(
        "<div style='text-align: center; padding: 15px; background-color: #f0f2f6; border-radius: 8px; margin-bottom: 20px;'>"
        "대화가 완료되었습니다. 새로운 대화를 시작하려면 사이드바의 '채팅 초기화' 버튼을 클릭하세요."
        "</div>",
        unsafe_allow_html=True
    )

# 저장된 토픽으로 대화 시작하기
if st.session_state.start_with_topic:
    prompt = st.session_state.start_with_topic
    
    # 사용자 메시지를 기록에 추가
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # 응답 생성 및 표시
    generate_response(prompt)
    
    # 사용한 토픽 초기화
    st.session_state.start_with_topic = None
    
    # 페이지 리프레시
    st.rerun()