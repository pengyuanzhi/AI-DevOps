"""
Memory Safety Service

Provides memory safety analysis and fix suggestions for C/C++ code.
"""
import asyncio
from typing import Dict, List, Any, Optional
from pathlib import Path

from .valgrind import MemorySafetyAnalyzer, MemoryError, MemoryErrorType, MemoryErrorSeverity


class MemorySafetyService:
    """Memory safety analysis and fix suggestion service"""

    def __init__(self):
        self.analyzer = MemorySafetyAnalyzer()

    async def analyze(
        self,
        executable: str,
        build_dir: str = ".",
        use_ai_filtering: bool = True,
    ) -> Dict[str, Any]:
        """
        Analyze memory safety of executable

        Args:
            executable: Path to executable
            build_dir: Build directory
            use_ai_filtering: Use AI to filter false positives

        Returns:
            Analysis results with score and errors
        """
        result = await self.analyzer.analyze_memory_safety(
            executable=executable,
            build_dir=build_dir,
            use_ai_filtering=use_ai_filtering,
        )

        # Generate fix suggestions for errors
        if result.get("errors"):
            result["fix_suggestions"] = await self._generate_fix_suggestions(result["errors"])

        return result

    async def _generate_fix_suggestions(
        self,
        errors: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate AI-powered fix suggestions for memory errors"""
        from ....core.llm.factory import get_llm_client

        llm_client = get_llm_client()

        suggestions = []

        # Group errors by type
        error_groups: Dict[str, List[Dict]] = {}
        for error in errors[:10]:  # Limit to 10 for efficiency
            error_type = error["type"]
            if error_type not in error_groups:
                error_groups[error_type] = []
            error_groups[error_type].append(error)

        # Generate suggestions for each error type
        for error_type, type_errors in error_groups.items():
            # Pick a representative error
            error = type_errors[0]

            prompt = f"""You are a C++ memory safety expert. Analyze this memory error and provide a specific fix suggestion.

Error Type: {error_type}
Severity: {error['severity']}
Description: {error['what']}
Location: {error.get('source_file', 'unknown')}:{error.get('source_line', 0)}

Backtrace:
{chr(10).join(error.get('backtrace', [])[:5])}

Provide a fix suggestion that includes:
1. Root cause explanation (1-2 sentences)
2. Specific code fix (modern C++ preferred)
3. Best practice recommendation

Format as JSON:
{{
  "root_cause": "...",
  "code_fix": "...",
  "recommendation": "..."
}}
"""

            try:
                response = await llm_client.complete(prompt, max_tokens=800)

                import json
                suggestion_data = json.loads(response.strip())

                suggestions.append({
                    "error_type": error_type,
                    "affected_files": list(set(e.get("source_file", "") for e in type_errors if e.get("source_file"))),
                    "occurrence_count": len(type_errors),
                    "suggestion": suggestion_data,
                })

            except Exception as e:
                # Fallback to generic suggestion
                suggestions.append({
                    "error_type": error_type,
                    "affected_files": list(set(e.get("source_file", "") for e in type_errors if e.get("source_file"))),
                    "occurrence_count": len(type_errors),
                    "suggestion": {
                        "root_cause": self._get_generic_root_cause(error_type),
                        "code_fix": self._get_generic_fix(error_type),
                        "recommendation": self._get_generic_recommendation(error_type),
                    },
                })

        return suggestions

    def _get_generic_root_cause(self, error_type: str) -> str:
        """Get generic root cause for error type"""
        causes = {
            "leak": "Memory was allocated but never freed, causing a memory leak",
            "invalid_free": "Attempting to free memory that was not allocated or was already freed",
            "mismatched_free": "Memory was allocated with new[] but freed with free (or vice versa)",
            "invalid_read": "Reading from memory that has not been allocated or is invalid",
            "invalid_write": "Writing to memory that has not been allocated or is invalid",
            "conditional_jump_uninit": "Making a decision based on an uninitialized variable",
        }
        return causes.get(error_type, "Unknown memory error")

    def _get_generic_fix(self, error_type: str) -> str:
        """Get generic code fix for error type"""
        fixes = {
            "leak": """Use smart pointers instead of raw pointers:
// Before (leak)
int* ptr = new int(42);
// ... use ptr ...

// After (no leak)
auto ptr = std::make_unique<int>(42);
// ... use ptr ...
// Automatic cleanup when ptr goes out of scope""",

            "invalid_free": """Ensure proper ownership:
// Use smart pointers to track ownership
std::unique_ptr<int> ptr = std::make_unique<int>(42);
// No manual delete needed""",

            "mismatched_free": """Match allocation and deallocation:
// Wrong
int* arr = new int[10];
delete arr;  // Should be delete[]

// Right
int* arr = new int[10];
delete[] arr;

// Better: Use std::vector
std::vector<int> arr(10);""",

            "invalid_read": """Validate array bounds:
// Before
for (int i = 0; i <= 10; i++)  // Off-by-one!
    arr[i] = i;

// After
for (size_t i = 0; i < 10; i++)  // Correct bounds
    arr[i] = i;

// Better: Use range-based for
std::array<int, 10> arr;
for (auto& val : arr)
    val = 0;""",

            "invalid_write": """Validate array bounds before write:
// Use std::vector::at() for bounds checking
std::vector<int> vec(10);
try {
    vec.at(5) = 42;  // Throws std::out_of_range if invalid
} catch (const std::out_of_range& e) {
    // Handle error
}""",

            "conditional_jump_uninit": """Always initialize variables:
// Before
int x;
if (condition)  // Uninitialized!

// After
int x = 0;  // or std::optional<int> x;
if (condition)
    x = calculate();
""",
        }
        return fixes.get(error_type, "// Review the code for proper memory management")

    def _get_generic_recommendation(self, error_type: str) -> str:
        """Get generic best practice recommendation"""
        recommendations = {
            "leak": "Use RAII and smart pointers (std::unique_ptr, std::shared_ptr) to manage memory automatically",
            "invalid_free": "Never mix manual memory management with smart pointers - use one consistently",
            "mismatched_free": "Prefer STL containers (std::vector) over C-style arrays to avoid memory management issues",
            "invalid_read": "Use std::vector::at(), std::array, or bounds checking to prevent invalid memory access",
            "invalid_write": "Use STL containers and their safe access methods instead of raw pointers",
            "conditional_jump_uninit": "Always initialize variables at declaration or use std::optional for truly optional values",
        }
        return recommendations.get(error_type, "Follow modern C++ best practices and use RAII for resource management")

    async def generate_suppression_file(
        self,
        errors: List[Dict[str, Any]],
        output_path: str = "valgrind.supp",
    ) -> str:
        """
        Generate Valgrind suppression file for known false positives

        Args:
            errors: List of memory errors
            output_path: Path to write suppression file

        Returns:
            Generated suppression file content
        """
        suppressions = []

        for error in errors:
            # Generate suppression for each error
            error_type = error["type"]
            source_file = error.get("source_file", "")

            # Only suppress errors in third-party code
            if source_file and not any(path in source_file for path in ["/usr/", "third_party/", "vendor/"]):
                continue

            suppression = """{{
   <suppression_name>
   {0}
   fun:{1}
   ...
}}
""".format(error_type, self._extract_function_name(error.get("backtrace", [])))
            suppressions.append(suppression)

        content = "# Valgrind suppression file for AI-CICD\n\n" + "\n".join(suppressions)

        # Write to file
        if output_path:
            Path(output_path).write_text(content)

        return content

    def _extract_function_name(self, backtrace: List[str]) -> str:
        """Extract function name from backtrace frame"""
        if not backtrace:
            return "unknown_function"

        # First frame is usually the culprit
        frame = backtrace[0]
        if "::" in frame:
            # Extract C++ function name
            parts = frame.split("::")
            return parts[-1].split("(")[0].strip()
        else:
            return "unknown_function"


# Singleton instance
memory_safety_service = MemorySafetyService()
