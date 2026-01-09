"""
OpenAI 格式的服务
支持工具调用和流式/非流式响应
"""
import json
import time
import logging
from logging.handlers import TimedRotatingFileHandler


from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from config import LOCAL_CFG
from schema import ChatCompletionRequest
from chat_handlers import chat_completion, chat_completion_stream

# -------------------- 配置日志 --------------------
log_handler = TimedRotatingFileHandler(
    filename='llm_server.log',   # 主日志文件名
    when='midnight',                    # 按天切分
    interval=1,                  # 每 1 天
    backupCount=5,               # 最多保留 5 个历史文件
    encoding='utf-8',
    utc=True                    # 使用本地时间
)

log_handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
))

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
))

logging.basicConfig(
    level=logging.INFO,
    handlers=[log_handler, console_handler]
)

logger = logging.getLogger(__name__)

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
        if req.stream:
            async def sse():
                try:
                    async for chunk in chat_completion_stream(
                        messages=req.messages,
                        temperature=req.temperature,
                        top_p=req.top_p,
                        max_tokens=req.max_tokens,
                        location=req.location,
                    ):
                        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                except Exception as e:
                    # ⚠️ 流式兜底，保证客户端能结束
                    data = {
                        "type": "error",
                        "message": str(e)
                    }
                    yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                finally:
                    yield "data: [DONE]\n\n"

            return StreamingResponse(
                sse(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )

        else:
            result = await chat_completion(
                messages=req.messages,
                stream=req.stream,
                temperature=req.temperature,
                top_p=req.top_p,
                max_tokens=req.max_tokens,
                location=req.location,
            )

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
