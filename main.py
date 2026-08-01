"""
论文智伴 - 云端精简版 API
独立运行，无需数据库，无需文件系统，仅依赖 4 个 Python 包。
部署到 Render.com 等免费云平台，7x24 小时在线。
"""

import os
import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# =========================================================================== #
#  配置（从环境变量读取，不依赖 .env 文件）
# =========================================================================== #
API_KEY = os.environ.get("LLM_API_KEY", "")
BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
MODEL = "doubao-seed-2-1-turbo-260628"
MAX_TOKENS = 4096
TIMEOUT = 180

# =========================================================================== #
#  提示词模板（从项目 base_prompt.py 移植）
# =========================================================================== #
BASE_CONSTRAINT = """
你是专业学术论文辅助工具，严格遵守如下规则，绝不违反：
1. 禁止直接生成完整论文正文、可直接提交的完整段落；
2. 仅提供大纲思路、文献分析、语句润色、格式规范、参考文献排版；
3. 所有输出仅供学习参考；
4. 回答末尾固定附带文字：【本内容仅作科研学习参考，请遵守学术规范，禁止直接抄袭】；
5. 输出条理清晰，分段展示内容。
"""

OUTLINE_PROMPT = """
你是论文大纲规划助手。根据用户提供专业、论文类型、题目生成分级目录。
支持：本科毕业论文、硕士论文、课程论文、大创报告。
只输出大纲标题，不要书写正文内容。
"""

LITERATURE_PROMPT = """
你是文献分析助手。根据传入文献原文，梳理：研究目标、方法、创新点、不足、可借鉴思路。
使用清晰列表形式输出，不要生成长篇散文。
"""

REF_FORMAT_PROMPT = """
你是参考文献格式整理助手，严格执行GB/T 7714《信息与文献 参考文献著录规则》。
识别文献信息，自动排版标准参考文献格式。多条文献分行展示。
"""

POLISH_PROMPT = """
你是学术语句润色助手。只优化用户已写好的原文，不能改写核心观点；
修正语病、优化学术书面表达；保留原有语义。区分两种版本：原始句子、润色后句子。
"""

FORMAT_CHECK_PROMPT = """
你是论文格式校对助手。检查文本里标题层级、段落规范、标点、图表命名、引用格式常见错误；
逐条列出问题，同时给出修改方案，不擅自改写原文。
"""

# =========================================================================== #
#  请求模型（与 Coze 插件 OpenAPI Schema 完全一致）
# =========================================================================== #
class OutlineRequest(BaseModel):
    subject: str
    paper_type: str
    title: str

class LiteratureAnalyzeRequest(BaseModel):
    paper_topic: str
    literature_content: str

class RefFormatRequest(BaseModel):
    raw_ref_info: str

class PolishRequest(BaseModel):
    raw_text: str

class FormatCheckRequest(BaseModel):
    paper_segment: str

class AcademicTaskResponse(BaseModel):
    code: int = 200
    msg: str = "执行成功"
    data: str = ""

# =========================================================================== #
#  LLM 调用（直接用 httpx，不依赖项目内部模块）
# =========================================================================== #
async def call_llm(system_prompt: str, user_content: str, temperature: float = 0.5) -> str:
    """调用火山引擎豆包 API，返回模型回复文本。"""
    if not API_KEY:
        return "LLM API Key 未配置，请设置环境变量 LLM_API_KEY。"

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": BASE_CONSTRAINT + "\n\n" + system_prompt},
            {"role": "user", "content": user_content},
        ],
        "max_tokens": MAX_TOKENS,
        "temperature": temperature,
    }

    async with httpx.AsyncClient(timeout=httpx.Timeout(TIMEOUT, connect=10.0)) as client:
        response = await client.post(
            f"{BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

# =========================================================================== #
#  FastAPI 应用
# =========================================================================== #
app = FastAPI(
    title="论文智伴 API",
    description="学术论文写作辅助智能体 - 云端精简版",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================================== #
#  调试端点（部署后排查环境变量问题，确认后可删）
# =========================================================================== #
@app.get("/debug", tags=["系统"])
async def debug_env():
    key = os.environ.get("LLM_API_KEY", "")
    return {
        "LLM_API_KEY_set": bool(key),
        "LLM_API_KEY_prefix": key[:10] + "..." if len(key) > 10 else "(empty)",
        "LLM_API_KEY_length": len(key),
        "all_env_keys": sorted([k for k in os.environ.keys() if not k.startswith("_")]),
    }

# =========================================================================== #
#  健康检查
# =========================================================================== #
@app.get("/health", tags=["系统"])
async def health_check():
    return {"status": "ok", "service": "paper_agent_cloud", "version": "2.0.0"}

# =========================================================================== #
#  5 个学术功能接口（路径和参数与 Coze 插件完全一致）
# =========================================================================== #
@app.post("/academic/outline", tags=["论文辅助功能"])
async def create_outline(req: OutlineRequest):
    """生成论文大纲"""
    user_content = f"""
专业方向：{req.subject}
论文类型：{req.paper_type}
论文题目：{req.title}
请生成结构化论文大纲
"""
    result = await call_llm(OUTLINE_PROMPT, user_content, temperature=0.4)
    return {"code": 200, "msg": "执行成功", "data": result}

@app.post("/academic/literature", tags=["论文辅助功能"])
async def analyze_literature(req: LiteratureAnalyzeRequest):
    """分析文献"""
    user_content = f"""
我的研究课题：{req.paper_topic}
下面是文献内容：
{req.literature_content}
帮我分析这篇文献核心信息以及对我课题的参考价值
"""
    result = await call_llm(LITERATURE_PROMPT, user_content, temperature=0.5)
    return {"code": 200, "msg": "执行成功", "data": result}

@app.post("/academic/reference", tags=["论文辅助功能"])
async def format_reference(req: RefFormatRequest):
    """参考文献格式化"""
    user_content = f"""
原始文献信息：
{req.raw_ref_info}
整理为标准GB/T 7714参考文献格式
"""
    result = await call_llm(REF_FORMAT_PROMPT, user_content, temperature=0.1)
    return {"code": 200, "msg": "执行成功", "data": result}

@app.post("/academic/polish", tags=["论文辅助功能"])
async def polish_text(req: PolishRequest):
    """学术文本润色"""
    user_content = f"需要润色的学术文字：\n{req.raw_text}"
    result = await call_llm(POLISH_PROMPT, user_content, temperature=0.3)
    return {"code": 200, "msg": "执行成功", "data": result}

@app.post("/academic/format_check", tags=["论文辅助功能"])
async def check_format(req: FormatCheckRequest):
    """论文格式检查"""
    user_content = f"""
待检查论文片段：
{req.paper_segment}
检查格式、标点、标题、引用规范错误，并给出修改建议
"""
    result = await call_llm(FORMAT_CHECK_PROMPT, user_content, temperature=0.2)
    return {"code": 200, "msg": "执行成功", "data": result}

# =========================================================================== #
#  根路径
# =========================================================================== #
@app.get("/", tags=["系统"])
async def root():
    return {
        "name": "论文智伴 API",
        "version": "2.0.0",
        "status": "running",
        "endpoints": {
            "outline": "POST /academic/outline",
            "literature": "POST /academic/literature",
            "reference": "POST /academic/reference",
            "polish": "POST /academic/polish",
            "format_check": "POST /academic/format_check",
            "health": "GET /health",
        },
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
