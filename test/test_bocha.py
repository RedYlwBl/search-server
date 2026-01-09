import time
import requests
import json
import logging

BOCHA_URL = "https://api.bochaai.com/v1/web-search"
BOCHA_API_KEY = "sk-002dd37ab08a4fa2ba65700afb8af396"

# ========== 测试问题集 ==========
# TEST_QUERIES = [
#     {"type": "新闻", "query": "今天有什么重要新闻"},
#     {"type": "天气", "query": "今天北京天气怎么样"},
#     {"type": "指数", "query": "今日纳斯达克指数"},
#     {"type": "百科", "query": "全国有多少个码头"},
# ]

TEST_QUERIES = [
{"type": "", "query": "今天钦州的天气怎么样啊（今日日期：2025年12月24日）"},

{"type": "","query": "最近钦州会下雨吗（今日日期：2025年12月24日）"},

{"type": "","query": "最近钦州这边还会有台风吗（今日日期：2025年12月24日）"},

{"type": "","query": "全国一共有多少个自动化码头（今日日期：2025年12月24日）"},

{"type": "","query": "广州港2024年吞吐量"},

{"type": "","query": "习近平总书记什么时候来的北部湾港"},

{"type": "","query": "习总习近平总书记是什么时候考察广西的呀"},

{"type": "","query": "股市大盘（今日日期：2025年12月24日）"},
    
]

# ========== 日志配置 ==========
# log_filename = "web_search_test_bocha.log"


logger = logging.getLogger("bocha_test")
logger.setLevel(logging.INFO)

# 避免重复添加 Handler
if not logger.handlers:
    # 控制台输出 Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 格式化
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s"
    )
    console_handler.setFormatter(formatter)

    # 添加到 logger
    logger.addHandler(console_handler)

def search_bocha(query: str) -> str:
    """搜索并返回格式化文本摘要（多行）"""
    headers = {
        "Authorization": f"Bearer {BOCHA_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gte-rerank",
        "query": query,
        "freshness": "noLimit",
        "summary": True,
        "count": 5,
    }

    start_time = time.time()
    resp = requests.post(
        BOCHA_URL,
        headers=headers,
        json=payload,
        timeout=30
    )
    latency = time.time() - start_time

    resp.raise_for_status()
    pages = resp.json()["data"]["webPages"]["value"]

    texts = []
    for i, p in enumerate(pages, 1):
        texts.append(
            f"【引用{i}】\n"
            f"标题：{p.get('name')}\n"
            f"摘要：{p.get('summary')}\n"
        )

    return "\n".join(texts), latency


def main():
    latencies = []

    logger.info("===== 开始 Bocha Web Search 测试 =====")

    for item in TEST_QUERIES:
        qtype = item["type"]
        query = item["query"]

        logger.info(f"\n>>> 测试类型：{qtype}\n>>> 问题：{query}")

        try:
            result, latency = search_bocha(query)
            latencies.append(latency)
            time.sleep(1.0)
            logger.info(
                "延迟：%.3f 秒\n搜索结果：\n%s\n%s",
                latency,
                result,
                "-" * 80
            )

        except Exception as e:
            logger.exception(
                "请求失败：%s\n%s",
                e,
                "-" * 80
            )

    if latencies:
        avg_latency = sum(latencies) / len(latencies)
        logger.info(
            "===== 测试完成 =====\n"
            "测试次数：%d\n"
            "平均延迟：%.3f 秒\n",
            len(latencies),
            avg_latency
        )


if __name__ == "__main__":
    main()
