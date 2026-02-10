"""AI 대화형 분석 페이지 — Super Agent (Cognito 인증 + 사용자별 메모리)"""
from __future__ import annotations

import sys
import uuid
from pathlib import Path

import streamlit as st

_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

st.set_page_config(page_title="AI Chat", page_icon="💬", layout="wide")
st.title("💬 AI 대화형 분석")
st.caption("Super Agent를 통해 자연어로 AWS 인프라를 분석합니다.")

# ── Cognito 인증 ──
from dashboard.auth import require_auth, logout  # noqa: E402

user = require_auth()
if user is None:
    st.stop()

user_id: str = user["username"]

# ── 세션 상태 초기화 ──
if "messages" not in st.session_state:
    st.session_state.messages = []
if "agent" not in st.session_state:
    st.session_state.agent = None
if "chat_session_id" not in st.session_state:
    st.session_state.chat_session_id = str(uuid.uuid4())


def _get_agent():
    """Super Agent 싱글턴 생성 (사용자별 메모리 훅 포함)"""
    if st.session_state.agent is None:
        try:
            from strands import Agent
            from strands.models import BedrockModel
            from agents.runtime_base import MODEL_ID
            from agents.super.agent import SYSTEM_PROMPT, TOOLS
            from dashboard.chat_memory import get_memory_hooks

            model = BedrockModel(model_id=MODEL_ID)
            memory_hooks = get_memory_hooks(
                user_id=user_id,
                session_id=st.session_state.chat_session_id,
            )
            hooks = [memory_hooks] if memory_hooks else []
            st.session_state.agent = Agent(
                model=model,
                tools=TOOLS,
                system_prompt=SYSTEM_PROMPT,
                hooks=hooks,
            )
        except Exception as e:
            st.error(f"Agent 초기화 실패: {e}")
            return None
    return st.session_state.agent


# ── 사이드바 ──
with st.sidebar:
    st.markdown(f"**{user_id}** ({user.get('email', '')})")
    if st.button("로그아웃", use_container_width=True):
        logout()
        st.rerun()

    st.divider()
    st.markdown("### 예시 질문")
    examples = [
        "현재 EC2 인스턴스 상태를 요약해줘",
        "최근 30일 비용이 얼마야?",
        "보안 발견 사항 중 CRITICAL은 뭐가 있어?",
        "비용이 올라간 원인을 분석해줘",
        "전체 자산 현황과 보안 이슈를 요약해줘",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": ex})
            st.rerun()

    if st.button("대화 초기화", type="secondary", use_container_width=True):
        st.session_state.messages = []
        st.session_state.agent = None
        st.session_state.chat_session_id = str(uuid.uuid4())
        st.rerun()

# ── 대화 이력 표시 ──
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ── 사용자 입력 ──
user_input = st.chat_input("AWS 인프라에 대해 질문하세요…")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

# 마지막 메시지가 user이면 응답 생성
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    query = st.session_state.messages[-1]["content"]
    agent = _get_agent()

    if agent:
        with st.chat_message("assistant"):
            with st.spinner("분석 중…"):
                try:
                    response = agent(query)
                    answer = response.message["content"][0]["text"]
                except Exception as e:
                    answer = f"Agent 호출 중 오류가 발생했습니다: {e}"

            st.markdown(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})
