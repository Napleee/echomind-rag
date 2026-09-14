"""轻量异步压测脚本：对运行中的 EchoMind 后端做并发压测，输出 QPS 与延迟分位数。

场景:
    documents   GET /api/documents 纯接口路径（框架 + 数据库吞吐）
    chat-cached POST /api/chat 同一热门问题（Redis 完整回答缓存全命中路径）
                —— 先发一次预热缓存，再正式压测

用法（在 backend/ 目录下）:
    python -m eval.load_test --scenario documents  --concurrency 10 --total 200
    python -m eval.load_test --scenario chat-cached --concurrency 20 --total 100

说明: 未缓存的 chat 链路包含 CPU 重排与外部 LLM 调用，其瓶颈是模型与 API 配额而非
服务本身，故不作为 HTTP 压测场景（检索延迟见 run_eval 的平均检索延迟指标）。
"""
import argparse
import asyncio
import sys
import time
from pathlib import Path

# 保证从任意工作目录运行都能 import 到 app 包
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import httpx  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="EchoMind 轻量压测")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="后端地址")
    parser.add_argument(
        "--scenario", choices=("documents", "chat-cached"), default="documents"
    )
    parser.add_argument("--concurrency", type=int, default=10, help="并发数")
    parser.add_argument("--total", type=int, default=100, help="总请求数")
    parser.add_argument("--question", default="V2 什么时候上线？", help="chat-cached 场景的问题")
    return parser.parse_args()


def percentile(sorted_latencies: list[float], p: float) -> float:
    """线性插值取分位数（避免为 3 个百分位引入 numpy 依赖差异）。"""
    if not sorted_latencies:
        return 0.0
    idx = (len(sorted_latencies) - 1) * p
    lo, hi = int(idx), min(int(idx) + 1, len(sorted_latencies) - 1)
    frac = idx - lo
    return sorted_latencies[lo] * (1 - frac) + sorted_latencies[hi] * frac


async def one_request(client: httpx.AsyncClient, scenario: str, question: str) -> tuple[float, int]:
    """发一个请求，返回 (耗时 ms, 状态码)；状态码非 2xx 记为 -1。"""
    t0 = time.perf_counter()
    if scenario == "documents":
        resp = await client.get("/api/documents")
        code = resp.status_code
    else:
        async with client.stream(
            "POST",
            "/api/chat",
            json={"question": question},
        ) as resp:
            code = resp.status_code
            async for _ in resp.aiter_lines():
                pass  # 消费完整流（与前端行为一致）
    ms = (time.perf_counter() - t0) * 1000
    return ms, code if code < 400 else -code  # 负数表示 HTTP 错误码


async def run(args: argparse.Namespace) -> None:
    latencies: list[float] = []
    errors = 0
    semaphore = asyncio.Semaphore(args.concurrency)

    async with httpx.AsyncClient(base_url=args.url, timeout=120) as client:
        # chat-cached 场景先预热缓存（同时验证服务可用）
        if args.scenario == "chat-cached":
            print("预热: 发送一次完整请求以填充回答缓存…")
            ms, code = await one_request(client, "chat", args.question)
            print(f"预热完成（{ms:.0f}ms, HTTP {abs(code)}）")

        async def worker():
            nonlocal errors
            async with semaphore:
                ms, code = await one_request(client, args.scenario, args.question)
                if code < 0:
                    errors += 1
                else:
                    latencies.append(ms)

        print(f"压测: {args.scenario} × {args.total} 请求，并发 {args.concurrency}")
        t0 = time.perf_counter()
        await asyncio.gather(*(worker() for _ in range(args.total)))
        wall = time.perf_counter() - t0

    latencies.sort()
    qps = len(latencies) / wall
    print("-" * 56)
    print(
        f"成功 {len(latencies)} / 失败 {errors}，总耗时 {wall:.1f}s，QPS {qps:.1f}\n"
        f"P50 {percentile(latencies, 0.50):8.1f}ms   "
        f"P95 {percentile(latencies, 0.95):8.1f}ms   "
        f"P99 {percentile(latencies, 0.99):8.1f}ms"
    )


def main() -> None:
    asyncio.run(run(parse_args()))


if __name__ == "__main__":
    main()
