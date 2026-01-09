import json
import logging
import os
import time
import requests
from typing import Literal
from config import BAIDU_URL, BAIDU_API_KEY, BOCHA_API_KEY, BOCHA_URL
logger = logging.getLogger(__name__) 

def search_bocha(query: str) -> dict:
    """
    搜索并返回简洁文本摘要
    注意：count 固定为 3，外部入参会被忽略
    """
    url = BOCHA_URL
    headers = {
        "Authorization": f"Bearer {BOCHA_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {"query": query, "freshness": "noLimit", "summary": True, "count": 5}
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    pages = resp.json()["data"]["webPages"]["value"]
    texts = []
    for i, p in enumerate(pages, 1):
        texts.append(
            f"【引用{i}】\n标题：{p['name']}\n摘要：{p['summary']}\n"
        )
    res = { 
            "code": 200,
            "msg": "\n".join(texts)
        }

    logger.info("\n".join(texts))
    return res


def search_baidu(query: str) -> dict:
    """
    调用百度 Web Search 接口
    - 正常：返回 filtered 的字符串
    - 任意异常：返回提示信息字符串
    """

    HEADERS = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {BAIDU_API_KEY}",
    }

    payload = {
        "messages": [{"role": "user", "content": query}],
        "edition": "lite",
        "search_source": "baidu_search_v2",
        "resource_type_filter": [
            {"type": "web", "top_k": 5},
            {"type": "video", "top_k": 0},
            {"type": "image", "top_k": 0},
            {"type": "aladdin", "top_k": 0},
        ],
    }

    start_time = time.time()

    try:
        response = requests.post(
            BAIDU_URL,
            headers=HEADERS,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            timeout=60
        )
        latency = time.time() - start_time
        response.encoding = "utf-8"
        # ---------- 状态码判断 ----------
        if response.status_code != 200:
            res = { 
                "code": 400,
                "msg": "搜索繁忙"
            }

            logger.error(
                "Baidu search failed\n"
                "query: %s\n"
                "status_code: %s\n"
                "response_text: %s",
                query,
                response.status_code,
                response.text
            )
            return res
        
        data = response.json()
        refs = data.get("references", [])

        filtered = [
            {
                "index": r.get("id"),
                "标题": r.get("title"),
                "内容": r.get("content"),
                "日期": r.get("date"),
                "rerank_score": r.get("rerank_score"),
                "authority_score": r.get("authority_score"),
            }
            for r in refs
        ]

        # 日志（保留延迟，仅用于观测）
        logger.info(
            json.dumps(
                {
                    "query": query,
                    "latency_sec": round(latency, 3),
                    "status_code": response.status_code,
                    "response": filtered,
                },
                ensure_ascii=False,
                indent=2
            )
        )
        res = {
            "code": 200,
            "msg": json.dumps(filtered, ensure_ascii=False, indent=2)
        }

        return res

    except Exception as e:
        # 所有异常统一兜底
        res = { 
            "code": 400,
            "msg": "搜索异常"
        }

        logger.exception(
            "Baidu search error\nquery: %s\nerror: %s",
            query,
            e
        )

        return res


def main():
    test_queries = [
        #{"type": "新闻", "query": "今天有什么重要新闻"},
        {"type": "天气", "query": "今日天气 广西壮族自治区钦州市，（今日日期：2026-01-08）"},
        {"type": "天气", "query": "今日天气 广西壮族自治区钦州市，（今日日期：2026-01-08）"},
        {"type": "天气", "query": "今日天气 广西壮族自治区钦州市，（今日日期：2026-01-08）"}
    ]

    print("===== 开始 Baidu Web Search 测试 =====")

    for item in test_queries:
        qtype = item["type"]
        query = item["query"]

        print("\n" + "=" * 60)
        print(f"测试类型：{qtype}")
        print(f"问题：{query}")

        result = search_baidu(query)

        if "异常" in result:
            print("❌ 搜索失败")
            print(result)
        else:
            print("✅ 搜索成功")
            print(result)

    print("\n===== 测试结束 =====")


def concurrent_test():
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import threading

    test_queries = [
        {"type": "新闻", "query": "今天有什么重要新闻"},
        {"type": "天气", "query": "今天北京天气怎么样"},
        {"type": "指数", "query": "今日纳斯达克指数"},
        {"type": "百科", "query": "全国有多少个码头"},
    ]

    concurrency = 5   # 👈 并发数，可调大/小
    total_tasks = 10  # 👈 总请求数

    print("===== 开始并发测试 =====")
    print(f"并发数: {concurrency}, 总请求数: {total_tasks}")

    success = 0
    failed = 0
    errors = []

    def task(task_id: int):
        query = test_queries[task_id % len(test_queries)]["query"]
        thread_name = threading.current_thread().name
        result = search_baidu(query)
        return task_id, thread_name, query, result

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [
            executor.submit(task, i)
            for i in range(total_tasks)
        ]

        for future in as_completed(futures):
            task_id, thread_name, query, result = future.result()

            if "异常" in result:
                failed += 1
                errors.append((task_id, thread_name, query, result))
            else:
                success += 1

    print("\n===== 并发测试结果 =====")
    print(f"成功: {success}")
    print(f"失败: {failed}")

    if errors:
        print("\n===== 失败详情（重点看这里） =====")
        for task_id, thread_name, query, err in errors:
            print("-" * 80)
            print(f"Task ID: {task_id}")
            print(f"Thread: {thread_name}")
            print(f"Query: {query}")
            print(f"Error: {err}")

    print("\n===== 并发测试结束 =====")

if __name__ == "__main__":
    main()