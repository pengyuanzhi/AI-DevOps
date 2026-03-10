"""
Memory Safety API

Endpoints for memory safety analysis using Valgrind.
"""
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional, List

from ...services.ai.memory_safety.service import memory_safety_service


router = APIRouter(prefix="/memory-safety", tags=["Memory Safety"])


class AnalyzeMemoryRequest(BaseModel):
    """Request to analyze memory safety"""
    executable: str = Field(..., description="Path to executable to analyze")
    build_dir: str = Field(default=".", description="Build directory")
    use_ai_filtering: bool = Field(default=True, description="Use AI to filter false positives")


class AnalyzeMemoryResponse(BaseModel):
    """Response with memory safety analysis"""
    success: bool
    score: Optional[float] = None
    total_errors: Optional[int] = None
    filtered_errors: Optional[int] = None
    errors: Optional[List[dict]] = None
    fix_suggestions: Optional[List[dict]] = None
    summary: Optional[dict] = None
    error: Optional[str] = None


class GenerateSuppressionRequest(BaseModel):
    """Request to generate suppression file"""
    errors: List[dict] = Field(..., description="List of memory errors")
    output_path: str = Field(default="valgrind.supp", description="Output file path")


class FixSuggestion(BaseModel):
    """Fix suggestion for a memory error"""
    error_type: str
    affected_files: List[str]
    occurrence_count: int
    suggestion: dict


@router.post("/analyze", response_model=AnalyzeMemoryResponse)
async def analyze_memory_safety(request: AnalyzeMemoryRequest):
    """
    Analyze memory safety of executable using Valgrind

    Runs Valgrind Memcheck to detect:
    - Memory leaks
    - Invalid memory access (read/write)
    - Use of uninitialized variables
    - Invalid free operations
    - Mismatched new/delete

    The analysis includes:
    - Memory safety score (0-100)
    - List of detected errors
    - AI-powered fix suggestions
    - False positive filtering
    """
    result = await memory_safety_service.analyze(
        executable=request.executable,
        build_dir=request.build_dir,
        use_ai_filtering=request.use_ai_filtering,
    )

    if result.get("success") is not None:
        return AnalyzeMemoryResponse(**result)
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result.get("error", "Failed to analyze memory safety"),
        )


@router.post("/suppression")
async def generate_suppression(request: GenerateSuppressionRequest):
    """
    Generate Valgrind suppression file for false positives

    Creates a suppression file that can be used with Valgrind
    to suppress known false positives from third-party libraries.
    """
    try:
        content = await memory_safety_service.generate_suppression_file(
            errors=request.errors,
            output_path=request.output_path,
        )

        return {
            "success": True,
            "content": content,
            "path": request.output_path,
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate suppression file: {str(e)}",
        )


@router.get("/error-types")
async def get_error_types():
    """
    Get list of supported memory error types

    Returns all memory error types that can be detected by Valgrind
    """
    return {
        "error_types": [
            {
                "type": "leak",
                "name": "Memory Leak",
                "description": "Memory was allocated but never freed",
                "severity": "critical",
            },
            {
                "type": "invalid_free",
                "name": "Invalid Free",
                "description": "Attempting to free memory that was not allocated",
                "severity": "critical",
            },
            {
                "type": "mismatched_free",
                "name": "Mismatched Free",
                "description": "Memory allocated with new[] but freed with free (or vice versa)",
                "severity": "critical",
            },
            {
                "type": "invalid_read",
                "name": "Invalid Read",
                "description": "Reading from invalid memory location",
                "severity": "high",
            },
            {
                "type": "invalid_write",
                "name": "Invalid Write",
                "description": "Writing to invalid memory location",
                "severity": "high",
            },
            {
                "type": "conditional_jump_uninit",
                "name": "Uninitialized Conditional Jump",
                "description": "Making decision based on uninitialized variable",
                "severity": "high",
            },
            {
                "type": "access_beyond_heap",
                "name": "Access Beyond Heap",
                "description": "Accessing memory beyond allocated heap block",
                "severity": "high",
            },
            {
                "type": "access_beyond_stack",
                "name": "Access Beyond Stack",
                "description": "Accessing memory beyond stack frame",
                "severity": "high",
            },
            {
                "type": "use_uninitialized",
                "name": "Use Uninitialized Value",
                "description": "Using a variable that was never initialized",
                "severity": "medium",
            },
        ]
    }


@router.get("/best-practices")
async def get_best_practices():
    """
    Get memory safety best practices for C/C++

    Returns a list of best practices to avoid memory errors
    """
    return {
        "best_practices": [
            {
                "category": "Smart Pointers",
                "practices": [
                    "Use std::unique_ptr for exclusive ownership",
                    "Use std::shared_ptr for shared ownership",
                    "Use std::make_unique and std::make_shared to create smart pointers",
                    "Never use raw pointers with manual new/delete",
                ],
            },
            {
                "category": "Container Usage",
                "practices": [
                    "Prefer std::vector over C-style arrays",
                    "Prefer std::string over C-style strings (char*)",
                    "Use std::array for fixed-size arrays",
                    "Use at() method for bounds-checked access",
                ],
            },
            {
                "category": "RAII",
                "practices": [
                    "Follow RAII (Resource Acquisition Is Initialization) principle",
                    "Use destructors for resource cleanup",
                    "Use std::lock_guard for mutex management",
                ],
            },
            {
                "category": "Initialization",
                "practices": [
                    "Always initialize variables at declaration",
                    "Use std::optional for optional values",
                    "Use constexpr for compile-time constants",
                    "Enable compiler warnings (-Wall -Wextra)",
                ],
            },
            {
                "category": "Memory Management",
                "practices": [
                    "Match new with delete and new[] with delete[]",
                    "Never free the same pointer twice",
                    "Set pointers to nullptr after delete",
                    "Use valgrind or AddressSanitizer during testing",
                ],
            },
        ],
        "tools": [
            {
                "name": "Valgrind Memcheck",
                "description": "Runtime memory error detector",
                "usage": "valgrind --tool=memcheck --leak-check=full ./executable",
            },
            {
                "name": "AddressSanitizer",
                "description": "Fast memory error detector (compile-time)",
                "usage": "gcc -fsanitize=address -g source.cpp",
            },
            {
                "name": "UndefinedBehaviorSanitizer",
                "description": "Undefined behavior detector",
                "usage": "gcc -fsanitize=undefined -g source.cpp",
            },
            {
                "name": "ThreadSanitizer",
                "description": "Data race detector",
                "usage": "gcc -fsanitize=thread -g source.cpp",
            },
        ],
    }
