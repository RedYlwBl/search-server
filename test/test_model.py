import asyncio
import time
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key="EMPTY",
    base_url="http://47.96.7.235:30000/v1"# "http://127.0.0.1:30000/v1",
)


model_name = "Qwen3-30B-A3B-Instruct-2507-AWQ"

N_RUNS = 5

system_prompt = """
你是一个专业、可靠、注重事实与逻辑一致性的智能助手。你的目标是帮助用户高效解决问题，并在回答中体现清晰的结构、明确的推理步骤和可操作的结论。

在回答问题时，请优先理解用户的真实意图，而不仅仅是表面问题。如果用户的问题存在歧义或信息不足，请在必要时提出合理的澄清假设，并在回答中说明这些假设。在不确定的情况下，不要编造事实，而应明确指出不确定性或给出多种可能的解释。

你的回答应尽量做到简洁但完整，避免无关冗余，同时确保关键背景、前提条件和结论清楚呈现。对于技术性问题，请使用准确的术语，并在需要时给出示例、步骤说明或简要代码片段，以帮助用户理解和实践。对于复杂问题，请先给出总体结论，再分点展开说明。

当用户的问题涉及决策或方案选择时，请客观分析不同方案的优缺点、适用场景和潜在风险，避免绝对化表述。除非用户明确要求，否则不要做价值判断或情绪化评价。

如果问题涉及外部工具、数据或搜索能力，而你本身无法直接获取最新信息，请明确说明这一限制，并在条件允许的情况下给出可行的替代方案或建议用户如何获取所需信息。

在整个对话中，请保持语气专业、友好、中立，避免使用夸张或营销式语言。你的最终目标是让用户在阅读你的回答后，能够清楚地理解问题、掌握解决思路，并能够独立采取下一步行动。

"""


async def run_once(run_id: int):
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "今日上证指数"},
    ]

    start_time = time.time()
    first_token_time = None

    stream = await client.chat.completions.create(
        model=model_name,
        messages=messages,
        temperature=0.1,
        max_tokens=4096,
        stream=True
    )

    async for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            if first_token_time is None:
                first_token_time = time.time()


    end_time = time.time()

    ttft = (first_token_time - start_time) * 1000
    total = (end_time - start_time) * 1000

    print(
        f"[第 {run_id:02d} 次] "
        f"首帧延迟: {ttft:.2f} ms | 总延迟: {total:.2f} ms"
    )

    return ttft, total


async def main():
    ttft_list = []
    total_list = []

    print(f"开始测试（共 {N_RUNS} 次）...\n")

    for i in range(1, N_RUNS + 1):
        ttft, total = await run_once(i)
        ttft_list.append(ttft)
        total_list.append(total)

        # 避免 GPU 波动过大，可适当 sleep
        await asyncio.sleep(0.2)

    avg_ttft = sum(ttft_list) / N_RUNS
    avg_total = sum(total_list) / N_RUNS

    print("\n====== 统计结果 ======")
    print(f"平均首帧延迟 (TTFT): {avg_ttft:.2f} ms")
    print(f"平均总延迟: {avg_total:.2f} ms")


if __name__ == "__main__":
    asyncio.run(main())

