"""사용자별 메모리 훅 팩토리 — 인증된 사용자 ID로 AIOpsMemoryHooks 생성"""
from __future__ import annotations

import logging

import streamlit as st

logger = logging.getLogger(__name__)


def get_memory_hooks(user_id: str, session_id: str):
    """사용자별 AIOpsMemoryHooks 인스턴스를 생성합니다.

    Args:
        user_id: 인증된 사용자의 Cognito username (actor_id로 사용)
        session_id: Streamlit 세션별 UUID

    Returns:
        AIOpsMemoryHooks 인스턴스 또는 None (메모리 설정 실패 시)
    """
    cache_key = f"memory_hooks_{user_id}_{session_id}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]

    try:
        from agents.memory import (
            AIOpsMemoryHooks,
            create_or_get_memory_resource,
            memory_client,
        )

        memory_id = create_or_get_memory_resource()
        if not memory_id:
            logger.warning("Memory resource not available")
            return None

        hooks = AIOpsMemoryHooks(
            memory_id=memory_id,
            client=memory_client,
            actor_id=user_id,
            session_id=session_id,
        )
        st.session_state[cache_key] = hooks
        logger.info(f"Created memory hooks for user={user_id}, session={session_id}")
        return hooks

    except Exception as e:
        logger.error(f"Failed to create memory hooks: {e}")
        return None
