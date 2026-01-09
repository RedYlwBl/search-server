# ========== 基础配置 ==========
BOCHA_URL = "https://api.bochaai.com/v1/web-search"
BOCHA_API_KEY = "sk-"

BAIDU_URL = "https://qianfan.baidubce.com/v2/ai_search/web_search"
BAIDU_API_KEY = ""

# ========== LLM 配置 ==========
LOCAL_CFG = {
    "api_key": "EMPTY",
    "base_url": "http://47.96.7.235:30001/v1",  # "http://localhost:30001/v1",
    "model": "Qwen3-30B-A3B-Instruct-2507-AWQ",
}

from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key=LOCAL_CFG["api_key"],
    base_url=LOCAL_CFG["base_url"],
)
