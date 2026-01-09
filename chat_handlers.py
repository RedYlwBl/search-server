"""
聊天处理逻辑（非流式和流式）
"""
import json
import uuid
import logging
from typing import AsyncGenerator, List, Dict, Any, Optional

from openai import AsyncOpenAI

from config import client, LOCAL_CFG
from schema import (
    FALLBACK_SYSTEM, LANGUAGE_MATCH_SYSTEM, TOOLS_DESC, Message, TOOL_RULE_SYSTEM, DATA_ACCURACY_SYSTEM,
    get_datatime_now
)
from utils import split_messages_by_role, truncate_by_rounds_and_chars
from query_utils import build_search_query, extract_province_city, optimize_search_query, is_weather_query
from search import search_baidu

logger = logging.getLogger(__name__)


async def chat_completion(
    messages: List[Message],
    stream: bool = False,
    temperature: float = 0.3,
    top_p: float = 0.95,
    max_tokens: int = 3000,
    location: Optional[str] = None,
) -> str:
    """
    非流式聊天补全
    """
    openai_messages = []
    for msg in messages:
        d = msg.model_dump(exclude_none=True)
        d["content"] = d.get("content") or ""
        openai_messages.append(d)

    openai_messages.append(get_datatime_now())
    openai_messages.append(TOOL_RULE_SYSTEM)

    # ========== 第一轮 ==========
    first_resp = await client.chat.completions.create(
        model=LOCAL_CFG["model"],
        messages=openai_messages,
        tools=TOOLS_DESC,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        stream=False,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    ) # type: ignore

    assistant_msg = first_resp.choices[0].message

    # ========== 没有工具调用：直接返回 ==========
    if not assistant_msg.tool_calls:
        return assistant_msg.content or ""

    # ========== 有工具调用 ==========
    openai_messages.append({
        "role": "assistant",
        "content": assistant_msg.content or "",
        "tool_calls": [
            {
                "id": tc.id,
                "type": tc.type,
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                }
            }
            for tc in assistant_msg.tool_calls
        ]
    })

    # ========== 执行工具（安全） ==========
    for tc in assistant_msg.tool_calls:
        tool_result = ""
        success = True

        try:
            args = json.loads(tc.function.arguments or "{}")
            if tc.function.name == "search":
                raw_query = args.get("query", "")
                final_query = build_search_query(raw_query)
                search_res = search_baidu(final_query)
                tool_result = search_res.get("msg", "")
                if search_res.get("code") != 200:
                    success = False
            else:
                success = False
                tool_result = f"Unknown tool: {tc.function.name}"

        except Exception as e:
            success = False
            tool_result = f"Tool execution failed: {str(e)}"

        # 把"失败语义"明确告诉模型
        openai_messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": json.dumps({
                "success": success,
                "result": tool_result
            }, ensure_ascii=False)
        })

    # ========== 第二轮 ==========
    second_resp = await client.chat.completions.create(
        model=LOCAL_CFG["model"],
        messages=openai_messages,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        stream=False,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )

    return second_resp.choices[0].message.content or "抱歉，我暂时无法给出可靠回答。"


async def chat_completion_stream(
    messages: List[Message],
    temperature: float = 0.3,
    top_p: float = 0.95,
    max_tokens: int = 3000,
    location: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    流式聊天补全
    """
    # ---------- 1. 消息转换和优化 ----------
    openai_messages = []
    for msg in messages:
        d = msg.model_dump(exclude_none=True)
        d["content"] = d.get("content") or ""
        openai_messages.append(d)
    

    
    logger.info(f"openai_messages {openai_messages}")
    openai_messages.append(LANGUAGE_MATCH_SYSTEM)
    openai_messages.append(FALLBACK_SYSTEM)
    openai_messages.append(DATA_ACCURACY_SYSTEM)
    openai_messages.append(TOOL_RULE_SYSTEM)
    openai_messages.append(get_datatime_now())
    
    
    # 在第一轮构建query时优化问题：如果最后一条用户消息涉及天气且有location，添加提示
    if location and openai_messages:
        last_user_msg = None
        for msg in reversed(openai_messages):
            if msg.get("role") == "user":
                last_user_msg = msg
                break
        location_city = extract_province_city(location)
        if last_user_msg and is_weather_query(last_user_msg.get("content", "")):
            # 检查用户消息中是否已经包含location
            location_hint = {
                "role": "system",
                "content": f"【用户所在地信息】用户当前所在位置：{location_city}。\n"
                            "当查询天气相关问题时，如果用户问题中没有明确指定地点，\n"
                            "请在search工具的query参数中包含此位置信息中的城市名称（注意忽略街道信息）。\n"
            }
            openai_messages.append(location_hint)

    
    system_msg, history = split_messages_by_role(openai_messages)

    # ---------- 截断历史 ----------
    history = truncate_by_rounds_and_chars(
        history,
        max_rounds=5,
        max_chars=8000,
    )

    openai_messages = [
        system_msg,
        *history
    ]

    # ---------- 2. 第一轮（流式） ----------
    try:
        first_resp = await client.chat.completions.create(
            model=LOCAL_CFG["model"],
            messages=openai_messages,
            tools=TOOLS_DESC,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stream=True,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        ) # type: ignore
    except Exception as e:
        # 创建请求就失败
        yield {
            "type": "error",
            "stage": "create_first_completion",
            "message": str(e),
        }
        return

    assistant_content = ""
    tool_call_buffers: Dict[int, Dict[str, Any]] = {}

    try:
        async for chunk in first_resp:
            if not chunk.choices:
                continue

            delta = chunk.choices[0].delta

            # ---- 普通文本 ----
            if delta.content:
                assistant_content += delta.content

            # ---- 工具调用（增量拼接）----
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index

                    if idx not in tool_call_buffers:
                        tool_call_buffers[idx] = {
                            "id": tc.id or f"call_{uuid.uuid4()}",
                            "type": "function",
                            "function": {"name": "", "arguments": ""},
                        }

                    if tc.function and tc.function.name:
                        tool_call_buffers[idx]["function"]["name"] = tc.function.name

                    if tc.function and tc.function.arguments:
                        tool_call_buffers[idx]["function"]["arguments"] += tc.function.arguments

            # 原样把模型 chunk 透传给前端
            yield chunk.model_dump()

    except Exception as e:
        yield {
            "type": "error",
            "stage": "first_stream",
            "message": str(e),
        }
        return

    # ---------- 3. 第一轮结束：是否需要工具 ----------
    if not tool_call_buffers:
        # 没有 tool，第一轮已经是最终答案
        return

    # ---------- 4. 构造 assistant 消息 ----------
    assistant_msg = {
        "role": "assistant",
        "content": assistant_content,
        "tool_calls": [
            tool_call_buffers[i] for i in sorted(tool_call_buffers.keys())
        ],
    }
    openai_messages.append(assistant_msg)

    # ---------- 5. 执行工具（非流式，但安全） ----------
    for tc in assistant_msg["tool_calls"]:
        success = True
        result = ""

        try:
            # 参数解析
            try:
                args = json.loads(tc["function"]["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {}

            # 调用 search
            if tc["function"]["name"] == "search":
                raw_query = args.get("query", "")
                # 优化查询：如果是天气查询且没有location，添加location
                final_query = optimize_search_query(raw_query)

                search_res = search_baidu(final_query)

                result = search_res.get("msg", "")
                if search_res.get("code") != 200:
                    success = False
                    # 把错误以 stream 形式返回给前端
                    yield {
                        "type": "tool_error",
                        "tool": "search",
                        "message": result,
                    }
            else:
                success = False
                result = f"Unknown tool: {tc['function']['name']}"

        except Exception as e:
            success = False
            result = f"Tool failed: {str(e)}"

            yield {
                "type": "tool_error",
                "tool": tc["function"]["name"],
                "message": result,
            }

        # 无论成功失败，都要把 tool 结果告诉模型
        openai_messages.append({
            "role": "tool",
            "tool_call_id": tc["id"],
            "content": json.dumps(
                {"success": success, "result": result},
                ensure_ascii=False
            ),
        })

    # ---------- 6. 第二轮（流式） ----------
    try:
        second_resp = await client.chat.completions.create(
            model=LOCAL_CFG["model"],
            messages=openai_messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stream=True,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        ) # type: ignore
    except Exception as e:
        yield {
            "type": "error",
            "stage": "create_second_completion",
            "message": str(e),
        }
        return

    try:
        async for chunk in second_resp:
            yield chunk.model_dump()

    except Exception as e:
        yield {
            "type": "error",
            "stage": "second_stream",
            "message": str(e),
        }
        return
