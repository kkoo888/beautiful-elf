"""ChatLLMProvider — LLMProvider → LangChain BaseChatModel 适配器

这是统一两条路径的关键：
  LangGraph/LangChain 内部调 _stream() → 转发到 LLMProvider.chat() → StreamEvent

上层 LangGraph 不知道底层换了，前端只认 StreamEvent。
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Iterator
from typing import Any, Optional

logger = logging.getLogger(__name__)

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from pydantic import PrivateAttr

from app.llm.protocol import LLMProvider
from app.llm.types import (
    ChatConfig,
    DoneEvent,
    ErrorEvent,
    Message,
    TextDeltaEvent,
    ToolDefinition,
    ToolInputSchema,
    ToolUseDeltaEvent,
    ToolUseEndEvent,
    ToolUseStartEvent,
)


def _lc_messages_to_messages(messages: list[BaseMessage]) -> tuple[str, list[Message]]:
    """LangChain Message → LLMProvider Message

    Returns:
        (system_prompt, [Message])
    """
    system = ""
    result = []

    for m in messages:
        if isinstance(m, SystemMessage):
            system = m.content if isinstance(m.content, str) else str(m.content)
        elif isinstance(m, HumanMessage):
            result.append(Message(role="user", content=m.content if isinstance(m.content, str) else str(m.content)))
        elif isinstance(m, AIMessage):
            content = m.content if isinstance(m.content, str) else str(m.content)
            result.append(Message(role="assistant", content=content))
        elif isinstance(m, ToolMessage):
            from app.llm.types import ContentBlockToolResult
            result.append(Message(
                role="user",
                content=[ContentBlockToolResult(
                    tool_use_id=m.tool_call_id,
                    content=m.content if isinstance(m.content, str) else str(m.content),
                    is_error=getattr(m, "status", "") == "error",
                )],
            ))
        else:
            content = m.content if isinstance(m.content, str) else str(m.content)
            result.append(Message(role="user", content=content))

    return system, result


def _build_tool_definitions(tools: list[Any] | None) -> list[ToolDefinition] | None:
    """LangChain tool / OpenAI dict → ToolDefinition"""
    if not tools:
        return None

    defs = []
    for tool in tools:
        # ── 原始 OpenAI dict 格式（with_structured_output 传入）──
        if isinstance(tool, dict):
            func = tool.get("function", {})
            name = func.get("name", "")
            desc = func.get("description", "")
            schema = func.get("parameters", {"type": "object", "properties": {}})
            defs.append(ToolDefinition(
                name=name,
                description=desc,
                input_schema=ToolInputSchema(
                    type="object",
                    properties=schema.get("properties", {}),
                    required=schema.get("required", []),
                ),
            ))
            continue

        # ── LangChain StructuredTool 格式 ──
        name = getattr(tool, "name", "")
        desc = getattr(tool, "description", "")
        args_schema = getattr(tool, "args_schema", None)

        if args_schema:
            if hasattr(args_schema, "model_json_schema"):
                schema = args_schema.model_json_schema()
            elif hasattr(args_schema, "schema"):
                schema = args_schema.schema()
            else:
                schema = {"type": "object", "properties": {}}
        else:
            schema = {"type": "object", "properties": {}}

        defs.append(ToolDefinition(
            name=name,
            description=desc,
            input_schema=ToolInputSchema(
                type="object",
                properties=schema.get("properties", {}),
                required=schema.get("required", []),
            ),
        ))

    return defs or None


class ChatLLMProvider(BaseChatModel):
    """LLMProvider → LangChain BaseChatModel 适配器

    用法::

        from app.llm import llm_runtime
        from app.llm.langchain_adapter import ChatLLMProvider

        provider = llm_runtime.from_db_provider(db_provider, "deepseek-chat")
        llm = ChatLLMProvider(provider=provider)

        # 和 ChatOpenAI 一样的用法
        result = await llm.ainvoke([HumanMessage(content="你好")])

        # 流式
        async for chunk in llm.astream([HumanMessage(content="你好")]):
            print(chunk.content, end="")

        # 带工具
        llm_with_tools = llm.bind_tools([my_tool])
        result = await llm_with_tools.ainvoke([HumanMessage(content="...")])
    """

    provider: LLMProvider
    temperature: float = 0.7
    max_tokens: int = 4096
    _bound_tools: list[Any] = PrivateAttr(default=[])  # 存储 bind_tools 绑定的工具
    _bound_tool_choice: Any = PrivateAttr(default=None)  # 存储 tool_choice

    class Config:
        arbitrary_types_allowed = True

    def bind_tools(self, tools: list[Any], **kwargs: Any) -> "ChatLLMProvider":
        """绑定工具 — 返回新实例，工具存储在 _bound_tools 中。

        兼容 LangChain BaseChatModel 接口，engine.py 动态绑定工具时调用。
        """
        new = self.model_copy()
        new._bound_tools = list(tools)
        new._bound_tool_choice = kwargs.get("tool_choice", None)
        return new

    def with_structured_output(self, schema: Any, method: str = "json_schema", **kwargs: Any) -> Any:
        """结构化输出 — 对标 langchain-openai 官方实现

        官方源码 (langchain-openai 1.3.2):
          tool_name = convert_to_openai_tool(schema)["function"]["name"]
          llm = self.bind_tools([schema], tool_choice=tool_name, parallel_tool_calls=False)
          output_parser = PydanticToolsParser / JsonOutputKeyToolsParser
        """
        from langchain_core.runnables import RunnableLambda
        from langchain_core.utils.function_calling import convert_to_openai_tool
        import json

        # 官方方式: convert_to_openai_tool 转换 schema
        tool_def = convert_to_openai_tool(schema)
        tool_name = tool_def["function"]["name"]

        # 官方方式: tool_choice = 字符串（不是 dict！）
        llm_with_tools = self.bind_tools(
            [schema],
            tool_choice=tool_name,
            parallel_tool_calls=False,
        )

        def _parse_response(response: Any) -> Any:
            """从 tool_calls 解析（官方: PydanticToolsParser 逻辑）"""
            if hasattr(response, "tool_calls") and response.tool_calls:
                for tc in response.tool_calls:
                    args = tc.get("args", {})
                    if args:
                        try:
                            return schema(**args)
                        except Exception:
                            pass
            # fallback: content JSON 解析
            content = ""
            if hasattr(response, "content"):
                content = response.content if isinstance(response.content, str) else str(response.content)
            try:
                import re
                match = re.search(r'\{[\s\S]*\}', content)
                if match:
                    data = json.loads(match.group())
                    return schema(**data)
            except Exception:
                pass
            return None

        async def _async_invoke(messages):
            """异步调用"""
            msgs = messages if isinstance(messages, list) else [messages]
            resp = await llm_with_tools.ainvoke(msgs)
            result = _parse_response(resp)
            if result:
                return result
            # fallback: json_mode
            json_instruction = f"\n\n请严格按以下 JSON schema 返回数据，只输出 JSON:\n{json.dumps(tool_def['function']['parameters'], ensure_ascii=False)}"
            prompt_msgs = list(msgs)
            if prompt_msgs:
                last = prompt_msgs[-1]
                if hasattr(last, "content"):
                    prompt_msgs[-1] = HumanMessage(content=str(last.content) + json_instruction)
                else:
                    prompt_msgs.append(HumanMessage(content=json_instruction))
            resp = await self.ainvoke(prompt_msgs)
            return _parse_response(resp)

        def _sync_invoke(messages):
            """同步调用"""
            import asyncio
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            coro = _async_invoke(messages if isinstance(messages, list) else [messages])
            if loop and loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, coro).result(timeout=60)
            return asyncio.run(coro)

        return RunnableLambda(func=_sync_invoke, afunc=_async_invoke)


    @property
    def _llm_type(self) -> str:
        return f"llm-provider-{self.provider.provider_name}"

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """同步生成 — 在 async 环境中跑异步代码"""
        system, llm_messages = _lc_messages_to_messages(messages)
        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        temperature = kwargs.get("temperature", self.temperature)
        tool_defs = _build_tool_definitions(self._bound_tools) if self._bound_tools else None

        config = ChatConfig(
            max_tokens=max_tokens,
            temperature=temperature,
            system=system or None,
            stop_sequences=stop or [],
            tool_choice=self._bound_tool_choice,
        )

        text_parts: list[str] = []
        accumulated_tool_calls: dict[str, dict] = {}

        async def _collect():
            async for event in self.provider.chat(llm_messages, tools=tool_defs, config=config):
                if isinstance(event, TextDeltaEvent):
                    text_parts.append(event.text)
                elif isinstance(event, ToolUseStartEvent):
                    accumulated_tool_calls[event.tool_use_id] = {
                        "id": event.tool_use_id,
                        "name": event.tool_name,
                        "args": {},
                    }
                elif isinstance(event, ToolUseEndEvent):
                    tc = accumulated_tool_calls.get(event.tool_use_id)
                    if tc:
                        tc["args"] = event.arguments or {}

        # 在已有 event loop 中运行
        try:
            loop = asyncio.get_running_loop()
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, _collect())
                future.result(timeout=120)
        except RuntimeError:
            asyncio.run(_collect())

        tool_calls = list(accumulated_tool_calls.values()) if accumulated_tool_calls else []
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(
                content="".join(text_parts),
                tool_calls=tool_calls,
            ))],
        )

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        """同步流式 — 收集后一次性 yield（LangChain 同步流式在 async 环境中受限）

        真正的流式请用 _astream。
        """
        result = self._generate(messages, stop=stop, run_manager=run_manager, **kwargs)
        text = result.generations[0].message.content if result.generations else ""
        chunk = ChatGenerationChunk(message=AIMessageChunk(content=text))
        if run_manager:
            run_manager.on_llm_new_token(text, chunk=chunk)
        yield chunk

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        """异步生成 — 消费 StreamEvent，正确累积文本和工具调用"""
        text_parts: list[str] = []
        # tool_calls 按 id 累积（同一个 tool_call 可能分多个 chunk 到达）
        accumulated_tool_calls: dict[str, dict] = {}

        async for chunk in self._astream(messages, stop=stop, **kwargs):
            msg = chunk.message
            if msg.content:
                text_parts.append(msg.content)
            # 累积 tool_calls（AIMessageChunk.tool_calls 是 list[dict]）
            for tc in (msg.tool_calls or []):
                tc_id = tc.get("id", "")
                if tc_id and tc_id in accumulated_tool_calls:
                    accumulated_tool_calls[tc_id]["args"].update(tc.get("args", {}))
                elif tc_id:
                    accumulated_tool_calls[tc_id] = dict(tc)

        content = "".join(text_parts)
        tool_calls = list(accumulated_tool_calls.values()) if accumulated_tool_calls else []

        msg = AIMessage(content=content, tool_calls=tool_calls)
        return ChatResult(
            generations=[ChatGeneration(message=msg)],
        )

    async def _astream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any | None = None,
        **kwargs: Any,
    ):
        """异步流式 — 转发到 LLMProvider.chat()（核心路径）

        支持工具调用：将 ToolUse 事件转为 LangChain AIMessageChunk(tool_calls=...)。
        """
        system, llm_messages = _lc_messages_to_messages(messages)

        max_tokens = kwargs.get("max_tokens", self.max_tokens)
        temperature = kwargs.get("temperature", self.temperature)

        # 将绑定的 LangChain tool 转为 LLMProvider ToolDefinition
        tool_defs = _build_tool_definitions(self._bound_tools) if self._bound_tools else None

        config = ChatConfig(
            max_tokens=max_tokens,
            temperature=temperature,
            system=system or None,
            stop_sequences=stop or [],
            tool_choice=self._bound_tool_choice,
        )

        # 累积工具调用状态（一个流式 tool_call 分多个事件到达）
        _tool_calls: dict[str, dict] = {}  # tool_use_id → {id, name, args_str}

        async for event in self.provider.chat(llm_messages, tools=tool_defs, config=config):
            if isinstance(event, TextDeltaEvent):
                chunk = ChatGenerationChunk(
                    message=AIMessageChunk(content=event.text),
                )
                if run_manager:
                    await run_manager.on_llm_new_token(event.text, chunk=chunk)
                yield chunk

            elif isinstance(event, ToolUseStartEvent):
                _tool_calls[event.tool_use_id] = {
                    "id": event.tool_use_id,
                    "name": event.tool_name,
                    "args_str": "",
                }
                yield ChatGenerationChunk(
                    message=AIMessageChunk(
                        content="",
                        tool_calls=[{
                            "id": event.tool_use_id,
                            "name": event.tool_name,
                            "args": {},
                        }],
                    ),
                )

            elif isinstance(event, ToolUseDeltaEvent):
                tc = _tool_calls.get(event.tool_use_id)
                if tc:
                    tc["args_str"] += event.json_fragment

            elif isinstance(event, ToolUseEndEvent):
                tc = _tool_calls.get(event.tool_use_id)
                if tc:
                    try:
                        args = json.loads(tc["args_str"]) if tc["args_str"] else event.arguments or {}
                    except json.JSONDecodeError:
                        args = event.arguments or {}
                    yield ChatGenerationChunk(
                        message=AIMessageChunk(
                            content="",
                            tool_calls=[{
                                "id": tc["id"],
                                "name": tc["name"],
                                "args": args,
                            }],
                        ),
                    )

            elif isinstance(event, ErrorEvent):
                yield ChatGenerationChunk(
                    message=AIMessageChunk(content=f"[Error: {event.message}]"),
                )

    def _should_use_protocol_streaming(self, **kwargs: Any) -> bool:
        """内层 ainvoke 走 _agenerate 路径（id 合并 tool_calls）。

        三条路径对比：
          v2 protocol → AsyncChatModelStream → 丢失 tool_calls
          v1 stream   → generate_from_stream → 重复 tool_calls（append 而非按 id 合并）
          _agenerate  → 按 id 合并 tool_calls ✅

        注意：不影响外层 astream_events(version="v3")，只影响 ainvoke 内部。
        """
        return False

    def _should_stream(self, **kwargs: Any) -> bool:
        """同上，走 _agenerate 路径。"""
        return False

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {
            "provider": self.provider.provider_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }
