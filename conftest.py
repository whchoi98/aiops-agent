"""테스트 및 개발 환경을 위한 strands 모듈 스텁.

strands-agents 패키지가 설치되지 않은 환경(Python < 3.11 등)에서
도구 함수를 import하고 테스트할 수 있도록 @tool 데코레이터를 no-op으로 대체합니다.
"""

import sys
import types


def _ensure_strands_stub():
    """strands 패키지가 없을 때 스텁 모듈을 sys.modules에 주입합니다."""
    if "strands" in sys.modules:
        return

    # @tool 데코레이터를 no-op (원래 함수를 그대로 반환)으로 대체
    def tool(fn=None, **kwargs):
        if fn is not None:
            return fn
        return lambda f: f

    # strands 모듈 트리 구성
    strands_mod = types.ModuleType("strands")
    strands_mod.tool = tool

    strands_tools_mod = types.ModuleType("strands.tools")
    strands_tools_mod.tool = tool

    strands_mod.tools = strands_tools_mod

    # strands.models
    strands_models_mod = types.ModuleType("strands.models")

    class BedrockModel:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    strands_models_mod.BedrockModel = BedrockModel
    strands_mod.models = strands_models_mod

    # strands.Agent
    class Agent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.messages = []

        def __call__(self, prompt):
            return types.SimpleNamespace(
                message={"content": [{"text": f"Mock response to: {prompt}"}]}
            )

    strands_mod.Agent = Agent

    # strands.hooks
    strands_hooks_mod = types.ModuleType("strands.hooks")

    class HookProvider:
        pass

    class HookRegistry:
        def add_callback(self, event_type, callback):
            pass

    class MessageAddedEvent:
        pass

    class AfterInvocationEvent:
        pass

    strands_hooks_mod.HookProvider = HookProvider
    strands_hooks_mod.HookRegistry = HookRegistry
    strands_hooks_mod.MessageAddedEvent = MessageAddedEvent
    strands_hooks_mod.AfterInvocationEvent = AfterInvocationEvent
    strands_mod.hooks = strands_hooks_mod

    # strands.tools.mcp
    strands_tools_mcp_mod = types.ModuleType("strands.tools.mcp")

    class MCPClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def list_tools_sync(self):
            return []

    strands_tools_mcp_mod.MCPClient = MCPClient
    strands_tools_mod.mcp = strands_tools_mcp_mod

    # Register all modules
    sys.modules["strands"] = strands_mod
    sys.modules["strands.tools"] = strands_tools_mod
    sys.modules["strands.tools.tool"] = strands_tools_mod
    sys.modules["strands.tools.mcp"] = strands_tools_mcp_mod
    sys.modules["strands.models"] = strands_models_mod
    sys.modules["strands.hooks"] = strands_hooks_mod


# bedrock_agentcore 스텁
def _ensure_agentcore_stub():
    """bedrock_agentcore 패키지가 없을 때 스텁을 주입합니다."""
    if "bedrock_agentcore" in sys.modules:
        return

    agentcore_mod = types.ModuleType("bedrock_agentcore")

    # bedrock_agentcore.runtime
    runtime_mod = types.ModuleType("bedrock_agentcore.runtime")

    class BedrockAgentCoreApp:
        def __init__(self):
            self._entrypoint = None

        def entrypoint(self, fn):
            self._entrypoint = fn
            return fn

        def run(self):
            pass

    runtime_mod.BedrockAgentCoreApp = BedrockAgentCoreApp
    agentcore_mod.runtime = runtime_mod

    # bedrock_agentcore.memory
    memory_mod = types.ModuleType("bedrock_agentcore.memory")

    class MemoryClient:
        def __init__(self, **kwargs):
            pass

        def create_memory_and_wait(self, **kwargs):
            return {"id": "mock-memory-id"}

        def get_memory_strategies(self, memory_id):
            return []

        def retrieve_memories(self, **kwargs):
            return []

        def create_event(self, **kwargs):
            pass

        def delete_memory(self, **kwargs):
            pass

        class gmcp_client:
            @staticmethod
            def get_memory(**kwargs):
                return {}

    memory_mod.MemoryClient = MemoryClient

    # bedrock_agentcore.memory.constants
    memory_constants_mod = types.ModuleType("bedrock_agentcore.memory.constants")

    class StrategyType:
        SEMANTIC = types.SimpleNamespace(value="semantic")
        USER_PREFERENCE = types.SimpleNamespace(value="user_preference")

    memory_constants_mod.StrategyType = StrategyType
    memory_mod.constants = memory_constants_mod

    agentcore_mod.memory = memory_mod

    sys.modules["bedrock_agentcore"] = agentcore_mod
    sys.modules["bedrock_agentcore.runtime"] = runtime_mod
    sys.modules["bedrock_agentcore.memory"] = memory_mod
    sys.modules["bedrock_agentcore.memory.constants"] = memory_constants_mod


# mcp 스텁
def _ensure_mcp_stub():
    """mcp 패키지가 없을 때 스텁을 주입합니다."""
    if "mcp" in sys.modules:
        return

    mcp_mod = types.ModuleType("mcp")
    mcp_client_mod = types.ModuleType("mcp.client")
    mcp_streamable_mod = types.ModuleType("mcp.client.streamable_http")

    def streamablehttp_client(**kwargs):
        pass

    mcp_streamable_mod.streamablehttp_client = streamablehttp_client

    mcp_client_mod.streamable_http = mcp_streamable_mod
    mcp_mod.client = mcp_client_mod

    sys.modules["mcp"] = mcp_mod
    sys.modules["mcp.client"] = mcp_client_mod
    sys.modules["mcp.client.streamable_http"] = mcp_streamable_mod


# 모듈 로딩 전에 스텁 적용
_ensure_strands_stub()
_ensure_agentcore_stub()
_ensure_mcp_stub()
