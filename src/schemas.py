from pydantic import BaseModel
from typing import Literal
from datetime import datetime


class CommitData(BaseModel):
    hash: str
    short_hash: str
    author: str
    date: datetime
    message: str
    diff: str


class TemplateMeta(BaseModel):
    name: str
    description: str


class TemplateExecution(BaseModel):
    source: Literal["staged", "history"]
    limit: int = 1
    output_mode: Literal["auto", "clipboard", "file", "execute"] = "auto"


class TemplatePrompts(BaseModel):
    system: str | None = None
    user: str


class PromptTemplate(BaseModel):
    meta: TemplateMeta
    execution: TemplateExecution
    prompts: TemplatePrompts
