"""
AI分析相关API路由
"""

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from ...db.session import get_db_session
from ...services.ai.code_review import ai_code_review
from ...utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


class CodeReviewRequest(BaseModel):
    """代码审查请求"""
    project_id: int
    mr_id: int
    
    # 路径
    source_dir: str
    build_dir: str
    
    # 选项
    enable_clang_tidy: bool = True
    enable_cppcheck: bool = True
    use_ai_filtering: bool = True


@router.post("/code-review/trigger")
async def trigger_code_review(
    request: CodeReviewRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
):
    """
    触发AI增强代码审查
    """
    logger.info(
        "code_review_triggered",
        project_id=request.project_id,
        mr_id=request.mr_id,
    )
    
    # 在后台执行审查
    background_tasks.add_task(
        _execute_code_review,
        request,
    )
    
    return {
        "status": "pending",
        "message": "Code review started",
        "mr_id": request.mr_id,
    }


async def _execute_code_review(request: CodeReviewRequest):
    """在后台执行代码审查"""
    try:
        result = await ai_code_review.review_code(
            source_dir=request.source_dir,
            build_dir=request.build_dir,
            enable_clang_tidy=request.enable_clang_tidy,
            enable_cppcheck=request.enable_cppcheck,
            use_ai_filtering=request.use_ai_filtering,
        )
        
        logger.info(
            "code_review_completed",
            project_id=request.project_id,
            mr_id=request.mr_id,
            total_issues=result.total_issues,
            filtered_issues=result.filtered_issues,
            score=result.score.overall_score,
        )
        
        # TODO: 保存结果到数据库
        
    except Exception as e:
        logger.error(
            "code_review_failed",
            project_id=request.project_id,
            mr_id=request.mr_id,
            error=str(e),
        )


@router.get("/code-review/{mr_id}")
async def get_code_review_result(
    mr_id: int,
    db: Session = Depends(get_db_session),
):
    """
    获取代码审查结果
    """
    # TODO: 从数据库获取结果
    return {
        "mr_id": mr_id,
        "status": "completed",
        "score": {
            "overall": 85.5,
            "memory_safety": 90.0,
            "performance": 82.0,
            "modern_cpp": 88.0,
            "thread_safety": 85.0,
            "code_style": 82.0,
        },
        "issues": {
            "critical": 2,
            "warning": 15,
            "info": 30,
        },
    }
