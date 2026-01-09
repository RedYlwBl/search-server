"""
OpenAI 格式的服务
支持工具调用和流式/非流式响应
"""

import json
import time
import uuid
from typing import AsyncGenerator, List, Dict, Any, Union, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from openai import AsyncOpenAI

from search import search_bocha
from schema import Message, ChatCompletionRequest

# -------------------- 配置 --------------------
LOCAL_CFG = {
    "api_key": "EMPTY",
    "base_url": "http://47.96.7.235:30001/v1", #"http://localhost:30001/v1",
    "model": "Qwen3-30B-A3B-Instruct-2507-AWQ",
}

client = AsyncOpenAI(
    api_key=LOCAL_CFG["api_key"],
    base_url=LOCAL_CFG["base_url"],
)

# -------------------- 工具描述 --------------------
TOOLS_DESC = [
    {
        "type": "function",
        "function": {
            "name": "search_bocha",
            "description": "用于搜索最新的公开信息，包括但不限于天气、新闻、事件、人物、地点等实时或近期信息。当需要获取当前或最新的公开数据来回答问题时调用此工具。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词"},
                },
                "required": ["query"],
            },
        },
    }
]



# -------------------- 核心聊天逻辑 --------------------
async def chat_completion(
    messages: List[Message],
    stream: bool = False,
    temperature: float = 0.1,
    top_p: float = 0.95,
    max_tokens: int = 15000,
) -> Union[str, AsyncGenerator[Dict[str, Any], None]]:
    """
    核心聊天逻辑 - 默认使用工具
    """
    # 转换消息格式
    openai_messages = []
    for msg in messages:
        msg_dict = msg.model_dump(exclude_none=True)
        if msg_dict["content"] is None:
            msg_dict["content"] = ""
        openai_messages.append(msg_dict)
    
    # 第一轮：判断是否调用工具
    first_resp = await client.chat.completions.create(
        model=LOCAL_CFG["model"],
        messages=openai_messages,
        tools=TOOLS_DESC,  # 默认使用工具
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        stream=stream,
        extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    ) # type: ignore
    
    # 流式 主要
    if stream:
        async def stream_generator():
            assistant_msg = {"role": "assistant", "content": "", "tool_calls": []}
            tool_call_buffers = {}
            
            # 第一轮响应
            async for chunk in first_resp:
                if not chunk.choices:
                    continue
                
                delta = chunk.choices[0].delta
                
                if delta.content:
                    assistant_msg["content"] += delta.content or ""
                
                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in tool_call_buffers:
                            tool_call_buffers[idx] = {
                                "id": tc.id or f"call_{uuid.uuid4()}_{idx}",
                                "type": "function",
                                "function": {"name": "", "arguments": ""},
                            }
                        
                        if tc.function and tc.function.name:
                            tool_call_buffers[idx]["function"]["name"] = tc.function.name
                        
                        if tc.function and tc.function.arguments:
                            tool_call_buffers[idx]["function"]["arguments"] += tc.function.arguments or ""
                
                yield chunk.model_dump()
            
            # 检查是否有工具调用
            if tool_call_buffers:
                assistant_msg["tool_calls"] = [
                    tool_call_buffers[i] for i in sorted(tool_call_buffers.keys())
                ]
            
            # 如果有工具调用，执行并获取第二轮响应
            if assistant_msg["tool_calls"]:
                openai_messages.append(assistant_msg)
                
                # 执行工具调用
                for tool_call in assistant_msg["tool_calls"]:
                    try:
                        args = json.loads(tool_call["function"]["arguments"] or "{}")
                    except:
                        args = {}
                    
                    if tool_call["function"]["name"] == "search_bocha":
                        query = args.get("query", "")
                        result = search_bocha(query)
                        openai_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": result,
                        })
                
                # 第二轮响应
                second_resp = await client.chat.completions.create(
                    model=LOCAL_CFG["model"],
                    messages=openai_messages,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    stream=True,
                    extra_body={"chat_template_kwargs": {"enable_thinking": False}},
                )
                
                async for chunk in second_resp:
                    yield chunk.model_dump()
        
        return stream_generator()
    
    else:
        # 非流式响应
        assistant_message = first_resp.choices[0].message
        
        # 如果没有工具调用，直接返回
        if not assistant_message.tool_calls:
            return assistant_message.content or ""
        
        # 执行工具调用
        openai_messages.append({
            "role": "assistant",
            "content": assistant_message.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                }
                for tc in assistant_message.tool_calls
            ]
        })
        
        for tool_call in assistant_message.tool_calls:
            try:
                args = json.loads(tool_call.function.arguments or "{}")
            except:
                args = {}
            
            if tool_call.function.name == "search_bocha":
                query = args.get("query", "")
                result = search_bocha(query)
                openai_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result,
                })
        
        # 第二轮响应
        second_resp = await client.chat.completions.create(
            model=LOCAL_CFG["model"],
            messages=openai_messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stream=False,
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )
        
        return second_resp.choices[0].message.content or ""


# -------------------- FastAPI 实例 --------------------
app = FastAPI(title="OpenAI-Compatible API")


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest):
    """
    OpenAI 兼容的聊天补全接口
    """
    if req.model != LOCAL_CFG["model"]:
        raise HTTPException(400, f"Model not supported: {LOCAL_CFG['model']}")
    
    try:
        result = await chat_completion(
            messages=req.messages,
            stream=req.stream,
            temperature=req.temperature,
            top_p=req.top_p,
            max_tokens=req.max_tokens,
        )
        
        if req.stream:
            async def sse_generator():
                async for chunk in result:
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                yield "data: [DONE]\n\n"
            
            return StreamingResponse(
                sse_generator(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
            )
        
        else:
            return {
                "id": f"chatcmpl-{int(time.time())}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": req.model,
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": result},
                    "finish_reason": "stop",
                }],
                "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            }
    
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(500, f"Internal error: {str(e)}")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": time.time()}


@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [{
            "id": LOCAL_CFG["model"],
            "object": "model",
            "created": int(time.time()),
            "owned_by": "qibao_server",
        }]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=30000, log_level="info")