# EchoMind（回声）

> 让每一次发言都有回声。

基于 RAG 的文档知识库问答系统：上传会议记录、设计文档，即可随时提问，得到**带出处引用**的流式回答。

---

## 项目简介

RAG（Retrieval-Augmented Generation，检索增强生成）分两步：**先**把文档切块并向量化存入 pgvector，**再**在提问时检索出最相关的片段，拼进 Prompt 让大模型"看着证据回答"，从根源上抑制幻觉。EchoMind 在此基础上采用**混合检索**（向量语义召回 + BM25 关键词召回 → RRF 融合），让语义相近和精确匹配（型号、日期、人名）两条路都不漏。

```
  上传文档 ──▶ 入库管线（异步）                    提问 question
              parse ─▶ chunk ─▶ embed                 │
                 │                      ▼             ▼
                 │            ┌──────────────────────────────┐
                 │            │  PostgreSQL 16 + pgvector    │
                 │            │  chunks 表（HNSW 向量索引）    │
                 │            └──────────────────────────────┘
                 │                向量检索 Top20   BM25(jieba) Top20
                 │                        └───┬───┘
                 │                            ▼
                 │                     RRF 融合取 Top5
                 │                            ▼
                 │                LLM（DeepSeek / 无Key时 mock 回显）
                 │                            │
                 └──────────▶ SSE 流式回答 + chunk 级来源溯源 ◀── 前端(Vite :5173)
```

## 功能特性

**已完成**

- 文档上传：PDF / Word / Markdown / TXT / 会议 JSON，后台上传（202 异步），状态轮询与失败原因可见
- 中文友好切块：500 字符 + 50 字符相邻重叠，边界不断语义
- 本地向量化：bge-small-zh-v1.5（512 维，CPU 可跑，零 API 成本）
- 混合检索：向量（pgvector HNSW）+ BM25（jieba 分词）双路召回，RRF 融合
- 流式问答：SSE 逐 token 输出，回答附 chunk 级引用（文档名 + 原文片段 + 相似度得分）
- 多轮会话：会话与消息落库，刷新页面不丢上下文
- Mock 模式：不配置任何 API Key 即可全链路演示（LLM 层回显检索结果）
- 检索质量评估：`backend/eval` 内置 10 题测试集，一键计算 recall@k

**路线图**

- 重排器（bge-reranker，融合后精排）
- 完整评估体系（MRR / nDCG / 端到端答案正确率）
- Redis 问答缓存 + 压测 + 容器化部署

## 技术选型

| 层 | 技术 | 选型理由 |
| --- | --- | --- |
| Web 框架 | FastAPI + uvicorn | 原生 async，天然适配 SSE 流式；自动生成 /docs 接口文档 |
| 数据库 | PostgreSQL 16 + pgvector | 关系数据与向量一库搞定，不引入独立向量库（Milvus/Qdrant），运维成本最低；支持 HNSW 索引 |
| ORM | SQLAlchemy 2.0 | Python 生态事实标准，类型标注友好 |
| Embedding | BAAI/bge-small-zh-v1.5 | 中文检索效果好，512 维小模型本地 CPU 可跑，零成本零外发 |
| 关键词检索 | jieba + rank-bm25 | 纯 Python BM25，配合中文分词补齐精确词匹配短板 |
| 融合 | RRF（k=60） | 只依赖排名不依赖分数分布，无需调权，鲁棒性强 |
| LLM | DeepSeek（OpenAI 兼容协议） | 便宜且协议通用，改 `LLM_BASE_URL` 即可切智谱 GLM 等厂商 |
| 缓存 | Redis 7 | 阶段5 问答结果缓存与限流（已提前引入客户端） |
| 前端 | Vite 工程（frontend/，:5173） | 秒级热更新；EventSource 消费 SSE 实现打字机效果 |
| 部署 | Docker Compose | 一条命令拉起 pgvector + Redis，环境一致 |
| 测试 | pytest | 纯逻辑单测（切块、RRF）不触数据库、不下载模型 |

## 快速开始

前置要求：Docker、Python 3.12、Node.js 18+。

```bash
# 1) 启动数据库与缓存
docker compose up -d

# 2) 创建虚拟环境并安装后端依赖
python -m venv .venv
.venv\Scripts\activate        # Windows（macOS/Linux: source .venv/bin/activate）
pip install -r backend/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 3) 配置环境变量（LLM_API_KEY 可留空，走 mock 模式）
copy .env.example backend\.env        # macOS/Linux: cp .env.example backend/.env

# 4) 启动后端（在 backend/ 目录）
cd backend
uvicorn app.main:app --reload --port 8000

# 5) 启动前端（另开终端，在 frontend/ 目录）
npm install
npm run dev
```

浏览器访问 **http://localhost:5173**，上传 `samples/` 目录下的示例文档即可开始提问。
后端健康检查：http://localhost:8000/api/health （首次启动会自动下载 embedding 模型，走国内镜像）。

检索质量评估（在 backend/ 目录）：

```bash
python -m eval.run_eval            # 默认 recall@5
python -m eval.run_eval --k 10     # recall@10
python -m eval.run_eval --limit 3  # 只跑前 3 题
```

## 配置说明

所有配置通过 `.env`（放在 backend/ 目录）注入，见 `.env.example`：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `LLM_BASE_URL` | `https://api.deepseek.com` | OpenAI 兼容 base_url；智谱填 `https://open.bigmodel.cn/api/paas/v4` |
| `LLM_API_KEY` | 空 | **留空 = mock 模式**，不调 LLM 直接回显检索结果 |
| `LLM_MODEL` | `deepseek-chat` | 模型名；智谱示例 `glm-4-flash` |
| `EMBEDDING_MODEL` | `BAAI/bge-small-zh-v1.5` | 本地向量模型（512 维） |
| `HF_ENDPOINT` | `https://hf-mirror.com` | HuggingFace 国内镜像 |
| `CHUNK_SIZE` | `500` | 目标块大小（字符） |
| `CHUNK_OVERLAP` | `50` | 硬切长段时相邻块重叠（字符） |
| `VECTOR_TOP_K` | `20` | 向量召回条数 |
| `BM25_TOP_K` | `20` | BM25 召回条数 |
| `FINAL_TOP_K` | `5` | RRF 融合后送入 Prompt 的条数 |
| `RRF_K` | `60` | RRF 平滑常数 |
| `ENABLE_RERANK` | `false` | 阶段3 开启重排 |
| `RERANK_MODEL` | `BAAI/bge-reranker-base` | 重排模型 |
| `DATABASE_URL` | `postgresql+psycopg://echomind:echomind@localhost:5432/echomind` | 与 docker-compose.yml 一致；后端容器化时 localhost 改为 `db` |
| `REDIS_URL` | `redis://localhost:6379/0` | 阶段5 使用；容器化时 localhost 改为 `redis` |
| `UPLOAD_DIR` | `data/uploads` | 上传文件目录（已加入 .gitignore） |
| `MAX_UPLOAD_MB` | `20` | 单文件大小上限 |
| `CORS_ORIGINS` | `["http://localhost:5173","http://127.0.0.1:5173"]` | 跨域白名单（JSON 数组） |

## 项目结构

```
项目3/
├── docker-compose.yml          # pgvector PostgreSQL 16 + Redis 7
├── .env.example                # 环境变量模板（全中文注释）
├── README.md
├── samples/                    # 示例语料（设计笔记 + 会议转写 JSON）
├── backend/
│   ├── Dockerfile              # 后端镜像（python:3.12-slim）
│   ├── requirements.txt        # 依赖白名单
│   ├── app/
│   │   ├── main.py             # FastAPI 入口 + /api/health
│   │   ├── core/               # config.py（配置）/ db.py（引擎与会话）
│   │   ├── models/             # Document / Chunk / Conversation / Message
│   │   ├── schemas/            # Pydantic 请求/响应契约
│   │   ├── api/                # 路由：documents / chat（SSE）
│   │   └── services/           # parsers / chunker / embedder / retriever / reranker / llm / ingestion
│   ├── eval/                   # 检索质量评估（questions.yaml + run_eval.py）
│   └── tests/                  # 纯逻辑单测（test_chunker / test_rrf）
└── frontend/                   # Vite 前端（SSE 流式渲染 + 来源溯源）
```

## 面试考点

- **混合检索与 RRF 公式**：向量检索擅长语义泛化（"上线日期" ↔ "什么时候发布"），BM25 擅长精确词（"10 月 15"、"bge-small-zh-v1.5"），两路召回互补。RRF（Reciprocal Rank Fusion）按排名融合：`score(d) = Σ 1/(k + rank_i(d))`，k=60 起平滑作用——排名越靠前贡献越大，且**只看名次不看分数**，避免了向量余弦分与 BM25 分数分布不可比、需要调权重的问题。
- **HNSW 与 IVF 对比**：HNSW 是多层跳表式近邻图，查询近似 O(logN)、召回高，代价是内存大、构建慢；IVF 先聚类再只搜最近的 nprobe 个簇，内存省、构建快，但召回受 nprobe 影响需要调参。本项目数据量在百万级以下，选 HNSW（`vector_cosine_ops`）一步到位拿高召回低延迟；数据到亿级再考虑 IVF/HNSW 参数调优或分层方案。
- **chunk 策略**：块太大→单块语义稀释、检索精度下降、Prompt 变长变贵；块太小→上下文断裂、答案缺前因后果。取 500 字符 + 50 重叠：重叠保证句子被边界切断时语义不丢。后续可实验 256/512/1024 对照 recall 差异，用 `backend/eval` 直接量化。
- **评估计划**：当前 10 题测试集测 recall@k（期望关键词是否出现在 Top-k 检索块中）；阶段4 扩展为 MRR / nDCG 衡量排序质量，再加 LLM-as-judge 评端到端答案正确率与引用忠实度，并做 chunk 大小、召回条数、是否 rerank 的消融实验。
- **mock 模式的设计动机**：面试/演示环境网络不可控（Key 失效、厂商限流），mock 让检索→融合→引用溯源的主链路完全不依赖外部服务即可验证；同时倒逼 LLM 层接口先定型（`stream_answer(question, context_blocks)`），换真模型只是换实现，不动架构。

## Roadmap

- [x] 阶段1：基础设施 + 数据模型 + 文档入库管线
- [x] 阶段2：混合检索（向量 + BM25 + RRF）+ SSE 流式问答 + 前端
- [ ] 阶段3：重排（bge-reranker，`ENABLE_RERANK=true` 灰度开启）
- [ ] 阶段4：评估体系（recall@k → MRR / nDCG / 端到端正确率）
- [ ] 阶段5：Redis 问答缓存 + 压测 + 容器化部署

## License

MIT
