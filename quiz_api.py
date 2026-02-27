import json
import os
from contextlib import asynccontextmanager

try:
    from fastapi import FastAPI, HTTPException, Header
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("请先安装依赖：")
    print("  pip install fastapi uvicorn openai")
    raise SystemExit

from openai import OpenAI


PROMPT_TEMPLATE = """根据以下内容，生成一道单选题。
只返回 JSON，不要任何多余文字，格式如下：
{{
  "question": "题目内容",
  "options": {{"A": "选项A内容", "B": "选项B内容", "C": "选项C内容", "D": "选项D内容"}},
  "answer": "A",
  "explanation": "答案解析"
}}

用户输入内容：
{content}"""


app = FastAPI(
    title="AI 选择题生成器",
    description="输入任意内容，自动生成一道单选题",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    content: str
    api_key: str | None = None  # 可选，优先使用环境变量


class Option(BaseModel):
    A: str
    B: str
    C: str
    D: str


class QuizResponse(BaseModel):
    question: str
    options: Option
    answer: str
    explanation: str


@app.post("/generate", response_model=QuizResponse, summary="生成选择题")
def generate_quiz(req: GenerateRequest):
    """
    根据输入内容生成一道单选题。

    - **content**: 输入的文本内容或主题
    - **api_key**: DeepSeek API Key（也可通过环境变量 DEEPSEEK_API_KEY 设置）
    """
    api_key = req.api_key or os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="缺少 API Key，请在请求体或环境变量 DEEPSEEK_API_KEY 中提供")

    if not req.content.strip():
        raise HTTPException(status_code=400, detail="content 不能为空")

    try:
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        response = client.chat.completions.create(
            model="deepseek-chat",
            max_tokens=1024,
            messages=[{"role": "user", "content": PROMPT_TEMPLATE.format(content=req.content)}]
        )
        raw = response.choices[0].message.content.strip()
        start = raw.find("{")
        end = raw.rfind("}") + 1
        data = json.loads(raw[start:end])
        return data
    except json.JSONDecodeError:
        raise HTTPException(status_code=502, detail="AI 返回格式异常，请重试")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/", summary="健康检查")
def root():
    return {"status": "ok", "message": "AI 选择题生成器正在运行，访问 /docs 查看接口文档"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("quiz_api:app", host="0.0.0.0", port=port)
