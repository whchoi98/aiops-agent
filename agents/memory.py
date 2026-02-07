"""AgentCore Memory 통합 — 운영 컨텍스트 관리 (E2E lab2 패턴)"""
from __future__ import annotations

import logging
import uuid

import boto3
from bedrock_agentcore.memory import MemoryClient
from bedrock_agentcore.memory.constants import StrategyType
from boto3.session import Session
from strands.hooks import (
    AfterInvocationEvent,
    HookProvider,
    HookRegistry,
    MessageAddedEvent,
)

from agents.utils import get_ssm_parameter, put_ssm_parameter, SSM_PREFIX

boto_session = Session()
REGION = boto_session.region_name

logger = logging.getLogger(__name__)

ACTOR_ID = "ops_admin"
SESSION_ID = str(uuid.uuid4())

memory_client = MemoryClient(region_name=REGION)
MEMORY_NAME = "AIOpsMemory"


# ---------------------------------------------------------------------------
# Memory 리소스 생성 / 조회
# ---------------------------------------------------------------------------

def create_or_get_memory_resource() -> str | None:
    """AgentCore Memory 리소스를 생성하거나 기존 ID를 반환합니다."""
    try:
        memory_id = get_ssm_parameter(f"{SSM_PREFIX}/memory_id")
        memory_client.gmcp_client.get_memory(memoryId=memory_id)
        return memory_id
    except Exception:
        try:
            strategies = [
                {
                    StrategyType.SEMANTIC.value: {
                        "name": "OpsAnalysisSemantic",
                        "description": "인프라 분석 결과 및 인시던트 이력 저장",
                        "namespaces": ["ops/analysis/{actorId}/semantic"],
                    }
                },
                {
                    StrategyType.USER_PREFERENCE.value: {
                        "name": "OpsPreferences",
                        "description": "운영자 선호 설정 (알림 임계값, 관심 리소스 등)",
                        "namespaces": ["ops/admin/{actorId}/preferences"],
                    }
                },
            ]
            print("Creating AgentCore Memory resources...")
            response = memory_client.create_memory_and_wait(
                name=MEMORY_NAME,
                description="AIOps agent memory for operational context",
                strategies=strategies,
                event_expiry_days=90,
            )
            memory_id = response["id"]
            put_ssm_parameter(f"{SSM_PREFIX}/memory_id", memory_id)
            return memory_id
        except Exception:
            return None


def delete_memory(memory_hook: "AIOpsMemoryHooks") -> None:
    """Memory 리소스를 삭제합니다."""
    try:
        ssm_client = boto3.client("ssm", region_name=REGION)
        memory_client.delete_memory(memory_id=memory_hook.memory_id)
        ssm_client.delete_parameter(Name=f"{SSM_PREFIX}/memory_id")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Memory Hooks
# ---------------------------------------------------------------------------

class AIOpsMemoryHooks(HookProvider):
    """AIOps 운영 컨텍스트 메모리 훅"""

    def __init__(
        self,
        memory_id: str,
        client: MemoryClient,
        actor_id: str,
        session_id: str,
    ):
        self.memory_id = memory_id
        self.client = client
        self.actor_id = actor_id
        self.session_id = session_id
        self.namespaces = {
            i["type"]: i["namespaces"][0]
            for i in self.client.get_memory_strategies(self.memory_id)
        }

    def retrieve_ops_context(self, event: MessageAddedEvent) -> None:
        """이전 분석/인시던트 컨텍스트를 사용자 쿼리에 주입합니다."""
        messages = event.agent.messages
        if (
            messages[-1]["role"] == "user"
            and "toolResult" not in messages[-1]["content"][0]
        ):
            user_query = messages[-1]["content"][0]["text"]

            try:
                all_context: list[str] = []
                for context_type, namespace in self.namespaces.items():
                    memories = self.client.retrieve_memories(
                        memory_id=self.memory_id,
                        namespace=namespace.format(actorId=self.actor_id),
                        query=user_query,
                        top_k=3,
                    )
                    for memory in memories:
                        if isinstance(memory, dict):
                            content = memory.get("content", {})
                            if isinstance(content, dict):
                                text = content.get("text", "").strip()
                                if text:
                                    all_context.append(
                                        f"[{context_type.upper()}] {text}"
                                    )

                if all_context:
                    context_text = "\n".join(all_context)
                    original_text = messages[-1]["content"][0]["text"]
                    messages[-1]["content"][0]["text"] = (
                        f"Ops Context:\n{context_text}\n\n{original_text}"
                    )
                    logger.info(f"Retrieved {len(all_context)} ops context items")
            except Exception as e:
                logger.error(f"Failed to retrieve ops context: {e}")

    def save_ops_interaction(self, event: AfterInvocationEvent) -> None:
        """분석 결과/조치 이력을 저장합니다."""
        try:
            messages = event.agent.messages
            if len(messages) >= 2 and messages[-1]["role"] == "assistant":
                user_query = None
                agent_response = None

                for msg in reversed(messages):
                    if msg["role"] == "assistant" and not agent_response:
                        agent_response = msg["content"][0]["text"]
                    elif (
                        msg["role"] == "user"
                        and not user_query
                        and "toolResult" not in msg["content"][0]
                    ):
                        user_query = msg["content"][0]["text"]
                        break

                if user_query and agent_response:
                    self.client.create_event(
                        memory_id=self.memory_id,
                        actor_id=self.actor_id,
                        session_id=self.session_id,
                        messages=[
                            (user_query, "USER"),
                            (agent_response, "ASSISTANT"),
                        ],
                    )
                    logger.info("Saved ops interaction to memory")
        except Exception as e:
            logger.error(f"Failed to save ops interaction: {e}")

    def register_hooks(self, registry: HookRegistry) -> None:
        """Strands HookRegistry에 메모리 훅을 등록합니다."""
        registry.add_callback(MessageAddedEvent, self.retrieve_ops_context)
        registry.add_callback(AfterInvocationEvent, self.save_ops_interaction)
        logger.info("AIOps memory hooks registered")
