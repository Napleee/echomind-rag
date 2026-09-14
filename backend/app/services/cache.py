"""Redis 缓存与限流（fail-open: Redis 不可用时全部直通，不影响可用性）。

两层缓存:
    检索结果缓存  key = echomind:{ns}:q:{sha256(问题)}  → 检索结果 + 资料块，TTL 可配
    完整回答缓存  key = echomind:{ns}:a:{sha256(问题)}  → 完整回答文本，TTL 可配
失效策略: 命名空间版本号。知识库变更时 ns+1，旧 key 无需遍历删除，等 TTL 自然过期。

限流: Redis 固定窗口，按客户端 IP 每分钟 N 次提问（默认 10），超限返回 429。
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Optional

import redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_client: Optional[redis.Redis] = None
# 模块级标志位: 探测到 Redis 不可用后本次进程内不再重试（避免每次请求都超时等待）
_unavailable = False

NS_KEY = "echomind:ns"  # 命名空间版本号的 key


def _get_client() -> Optional[redis.Redis]:
    """懒加载 Redis 客户端单例；不可用时返回 None（fail-open）。"""
    global _client, _unavailable
    if _unavailable:
        return None
    if _client is None:
        settings = get_settings()
        _client = redis.Redis.from_url(
            settings.redis_url, socket_connect_timeout=1, socket_timeout=1, decode_responses=True
        )
    try:
        _client.ping()
    except redis.RedisError:
        _unavailable = True
        logger.warning("Redis 不可用，缓存与限流降级为直通（fail-open）")
        return None
    return _client


def _ns(client: redis.Redis) -> int:
    """当前命名空间版本号（不存在则初始化为 1）。"""
    ns = client.get(NS_KEY)
    return int(ns) if ns else 1


def _q_hash(question: str) -> str:
    """缓存 key 的问题摘要: SHA-256 前 32 位（展示用足够，碰撞概率可忽略）。"""
    return hashlib.sha256(question.encode("utf-8")).hexdigest()[:32]


# ---------- 检索结果缓存 ----------

def get_cached_retrieval(question: str) -> Optional[dict]:
    """命中返回 {"sources": [...], "context_blocks": [...]}，未命中/降级返回 None。"""
    client = _get_client()
    if client is None:
        return None
    try:
        raw = client.get(f"echomind:{_ns(client)}:q:{_q_hash(question)}")
        return json.loads(raw) if raw else None
    except (redis.RedisError, ValueError):
        return None


def cache_retrieval(question: str, sources: list[dict], context_blocks: list[str]) -> None:
    settings = get_settings()
    client = _get_client()
    if client is None:
        return
    try:
        client.set(
            f"echomind:{_ns(client)}:q:{_q_hash(question)}",
            json.dumps({"sources": sources, "context_blocks": context_blocks},
                       ensure_ascii=False),
            ex=settings.cache_ttl_seconds,
        )
    except redis.RedisError:
        pass  # 写缓存失败不影响主流程


# ---------- 完整回答缓存 ----------

def get_cached_answer(question: str) -> Optional[str]:
    client = _get_client()
    if client is None:
        return None
    try:
        return client.get(f"echomind:{_ns(client)}:a:{_q_hash(question)}")
    except redis.RedisError:
        return None


def cache_answer(question: str, answer: str) -> None:
    settings = get_settings()
    client = _get_client()
    if client is None:
        return
    try:
        client.set(
            f"echomind:{_ns(client)}:a:{_q_hash(question)}",
            answer,
            ex=settings.cache_ttl_seconds,
        )
    except redis.RedisError:
        pass


# ---------- 失效 ----------

def invalidate_cache() -> None:
    """知识库变更时调用: 命名空间版本号 +1，旧缓存全部失效（等 TTL 自然回收）。"""
    client = _get_client()
    if client is None:
        return
    try:
        client.incr(NS_KEY)
        logger.info("缓存命名空间已升级（知识库变更，旧缓存失效）")
    except redis.RedisError:
        pass


# ---------- 限流（固定窗口） ----------

def rate_limit(client_ip: str) -> tuple[bool, int]:
    """检查该 IP 当前分钟窗口的提问次数。

    返回 (allowed, retry_after_seconds)；Redis 降级时恒为 (True, 0)。
    """
    settings = get_settings()
    if settings.rate_limit_per_min <= 0:
        return True, 0  # 配置为 0/负数 = 关闭限流
    client = _get_client()
    if client is None:
        return True, 0
    bucket = int(time.time() // 60)
    key = f"echomind:rl:{client_ip}:{bucket}"
    try:
        count = client.incr(key)
        if count == 1:
            client.expire(key, 60)
        if count > settings.rate_limit_per_min:
            return False, 60 - int(time.time() % 60)
    except redis.RedisError:
        pass  # fail-open
    return True, 0
