"""
代码覆盖率收集器

支持gcov/lcov的覆盖率数据收集和报告生成
"""

import os
import asyncio
import re
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from ....core.logging.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CoverageData:
    """覆盖率数据"""
    file_path: str  # 源文件路径
    line_total: int = 0  # 总行数
    line_covered: int = 0  # 覆盖的行数
    line_percent: float = 0.0  # 行覆盖率

    branch_total: int = 0  # 总分支数
    branch_covered: int = 0  # 覆盖的分支数
    branch_percent: float = 0.0  # 分支覆盖率

    function_total: int = 0  # 总函数数
    function_covered: int = 0  # 覆盖的函数数
    function_percent: float = 0.0  # 函数覆盖率

    @property
    def line_coverage_str(self) -> str:
        """行覆盖率字符串"""
        return f"{self.line_percent:.2f}% ({self.line_covered}/{self.line_total})"


@dataclass
class CoverageReport:
    """覆盖率报告"""
    # 总体统计
    line_total: int = 0
    line_covered: int = 0
    line_percent: float = 0.0

    branch_total: int = 0
    branch_covered: int = 0
    branch_percent: float = 0.0

    function_total: int = 0
    function_covered: int = 0
    function_percent: float = 0.0

    # 按文件统计
    files: Dict[str, CoverageData] = field(default_factory=dict)

    # 未覆盖的行
    uncovered_lines: Dict[str, List[int]] = field(default_factory=dict)

    def add_file(self, file_data: CoverageData):
        """添加文件覆盖率数据"""
        self.files[file_data.file_path] = file_data

        # 更新总体统计
        self.line_total += file_data.line_total
        self.line_covered += file_data.line_covered
        self.branch_total += file_data.branch_total
        self.branch_covered += file_data.branch_covered
        self.function_total += file_data.function_total
        self.function_covered += file_data.function_covered

        # 计算百分比
        if self.line_total > 0:
            self.line_percent = (self.line_covered / self.line_total) * 100
        if self.branch_total > 0:
            self.branch_percent = (self.branch_covered / self.branch_total) * 100
        if self.function_total > 0:
            self.function_percent = (self.function_covered / self.function_total) * 100


class CoverageCollector:
    """
    覆盖率收集器

    使用gcov和lcov收集和处理覆盖率数据。
    """

    def __init__(self):
        self.gcov_available = False
        self.lcov_available = False

        # 检查工具是否可用
        self._check_tools()

    def _check_tools(self):
        """检查覆盖率工具是否可用"""
        try:
            result = subprocess.run(["gcov", "--version"], capture_output=True)
            self.gcov_available = result.returncode == 0
            logger.info("gcov_available", available=self.gcov_available)
        except FileNotFoundError:
            self.gcov_available = False
            logger.warning("gcov_not_found")

        try:
            result = subprocess.run(["lcov", "--version"], capture_output=True)
            self.lcov_available = result.returncode == 0
            logger.info("lcov_available", available=self.lcov_available)
        except FileNotFoundError:
            self.lcov_available = False
            logger.warning("lcov_not_found")

    async def collect_coverage(
        self,
        build_dir: str,
        source_dirs: List[str],
        output_dir: Optional[str] = None,
    ) -> Optional[CoverageReport]:
        """
        收集代码覆盖率

        Args:
            build_dir: 构建目录
            source_dirs: 源代码目录列表
            output_dir: 输出目录（可选）

        Returns:
            覆盖率报告
        """
        if not self.gcov_available:
            logger.warning("gcov_not_available_coverage_collection_skipped")
            return None

        logger.info(
            "coverage_collection_started",
            build_dir=build_dir,
            source_dirs=source_dirs,
        )

        try:
            # 1. 运行gcov生成覆盖率数据
            gcov_files = await self._run_gcov(build_dir)

            if not gcov_files:
                logger.warning("no_gcov_files_generated")
                return None

            # 2. 解析gcov输出
            report = CoverageReport()

            for gcov_file in gcov_files:
                file_data = self._parse_gcov_file(gcov_file)
                if file_data:
                    report.add_file(file_data)

            # 3. 如果lcov可用，生成详细的覆盖率报告
            if self.lcov_available and output_dir:
                await self._generate_lcov_report(
                    build_dir=build_dir,
                    source_dirs=source_dirs,
                    output_dir=output_dir,
                )

            logger.info(
                "coverage_collection_completed",
                line_percent=report.line_percent,
                branch_percent=report.branch_percent,
                function_percent=report.function_percent,
            )

            return report

        except Exception as e:
            logger.error(
                "coverage_collection_failed",
                error=str(e),
                exc_info=True,
            )
            return None

    async def _run_gcov(self, build_dir: str) -> List[Path]:
        """
        运行gcov生成覆盖率文件

        Args:
            build_dir: 构建目录

        Returns:
            生成的gcov文件列表
        """
        build_path = Path(build_dir)

        # 查找所有.gcda文件
        gcda_files = list(build_path.rglob("*.gcda"))

        if not gcda_files:
            logger.warning("no_gcda_files_found", build_dir=build_dir)
            return []

        logger.info("gcda_files_found", count=len(gcda_files))

        # 为每个.gcda文件运行gcov
        gcov_files = []

        for gcda_file in gcda_files:
            try:
                # 运行gcov
                process = await asyncio.create_subprocess_exec(
                    "gcov",
                    "-o", str(gcda_file.parent),
                    str(gcda_file),
                    cwd=build_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                stdout, stderr = await process.communicate()

                if process.returncode == 0:
                    # gcov生成的.gcov文件
                    gcov_file = build_path / f"{gcda_file.stem}.gcov"
                    if gcov_file.exists():
                        gcov_files.append(gcov_file)

            except Exception as e:
                logger.warning(
                    "gcov_execution_failed",
                    file=str(gcda_file),
                    error=str(e),
                )
                continue

        logger.info("gcov_files_generated", count=len(gcov_files))
        return gcov_files

    def _parse_gcov_file(self, gcov_file: Path) -> Optional[CoverageData]:
        """
        解析gcov文件

        Args:
            gcov_file: gcov文件路径

        Returns:
            覆盖率数据
        """
        try:
            with open(gcov_file, 'r') as f:
                lines = f.readlines()

            # 第一行包含源文件路径
            # 格式: -:0:Source:file.cpp
            source_file = None
            for line in lines:
                if line.startswith("Source:"):
                    source_file = line.split(":", 1)[1].strip()
                    break

            if not source_file:
                return None

            data = CoverageData(file_path=source_file)
            uncovered_lines = []

            for line in lines:
                line = line.strip()
                if not line or line.startswith("Source:"):
                    continue

                # gcov格式: execution_count:line_number:source_code
                parts = line.split(":", 2)
                if len(parts) < 2:
                    continue

                execution_count = parts[0].strip()
                line_number_str = parts[1].strip()

                try:
                    line_number = int(line_number_str)
                except ValueError:
                    continue

                # 忽略非代码行
                if execution_count == "-" or execution_count == "====":
                    continue

                try:
                    count = int(execution_count)
                    if count > 0:
                        data.line_covered += 1
                    else:
                        uncovered_lines.append(line_number)

                    data.line_total += 1

                except ValueError:
                    # 可能是"####"表示不可执行行
                    pass

            # 计算百分比
            if data.line_total > 0:
                data.line_percent = (data.line_covered / data.line_total) * 100

            # 保存未覆盖的行
            if uncovered_lines:
                data.uncovered_lines = uncovered_lines

            return data

        except Exception as e:
            logger.error(
                "gcov_parse_error",
                file=str(gcov_file),
                error=str(e),
            )
            return None

    async def _generate_lcov_report(
        self,
        build_dir: str,
        source_dirs: List[str],
        output_dir: str,
    ):
        """
        使用lcov生成覆盖率报告

        Args:
            build_dir: 构建目录
            source_dirs: 源代码目录列表
            output_dir: 输出目录
        """
        try:
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)

            # 1. 基准覆盖率数据
            baseline_file = output_path / "coverage.info"

            # 运行lcov --capture
            capture_cmd = [
                "lcov",
                "--capture",
                "--directory", build_dir,
                "--output-file", str(baseline_file),
            ]

            process = await asyncio.create_subprocess_exec(
                *capture_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.warning("lcov_capture_failed", error=stderr.decode())
                return

            # 2. 移除不需要的路径
            filtered_file = output_path / "coverage_filtered.info"

            remove_patterns = [
                "/usr/include/*",
                "/usr/lib/*",
                "build/*",
                "*/tests/*",
                "*/test/*",
            ]

            filter_cmd = [
                "lcov",
                "--remove", str(baseline_file),
                *remove_patterns,
                "--output-file", str(filtered_file),
            ]

            process = await asyncio.create_subprocess_exec(
                *filter_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            await process.communicate()

            # 3. 生成HTML报告
            html_dir = output_path / "html"

            genhtml_cmd = [
                "genhtml",
                str(filtered_file),
                "--output-directory", str(html_dir),
                "--title", "Code Coverage Report",
                "--legend",
                "--show-details",
            ]

            process = await asyncio.create_subprocess_exec(
                *genhtml_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            await process.communicate()

            logger.info(
                "lcov_report_generated",
                html_dir=str(html_dir),
            )

        except Exception as e:
            logger.error(
                "lcov_report_generation_failed",
                error=str(e),
                exc_info=True,
            )

    async def get_quick_coverage(
        self,
        build_dir: str,
    ) -> Optional[float]:
        """
        快速获取总体覆盖率百分比

        Args:
            build_dir: 构建目录

        Returns:
            覆盖率百分比
        """
        if not self.gcov_available:
            return None

        try:
            build_path = Path(build_dir)
            gcda_files = list(build_path.rglob("*.gcda"))

            if not gcda_files:
                return None

            total_lines = 0
            covered_lines = 0

            # 只统计前几个文件以加快速度
            for gcda_file in gcda_files[:5]:
                process = await asyncio.create_subprocess_exec(
                    "gcov",
                    "-o", str(gcda_file.parent),
                    str(gcda_file),
                    cwd=build_dir,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                stdout, stderr = await process.communicate()

                if process.returncode == 0:
                    # 解析输出
                    output = stdout.decode()
                    match = re.search(r'Lines executed:(\d+\.\d+)%', output)
                    if match:
                        continue  # 从.gcov文件获取更准确的数据

                    # 解析.gcov文件
                    gcov_file = build_path / f"{gcda_file.stem}.gcov"
                    if gcov_file.exists():
                        data = self._parse_gcov_file(gcov_file)
                        if data:
                            total_lines += data.line_total
                            covered_lines += data.line_covered

            if total_lines > 0:
                return (covered_lines / total_lines) * 100

            return None

        except Exception as e:
            logger.error("quick_coverage_error", error=str(e))
            return None

    def format_coverage_report(self, report: CoverageReport) -> str:
        """
        格式化覆盖率报告

        Args:
            report: 覆盖率报告

        Returns:
            格式化的报告文本
        """
        lines = [
            "=" * 80,
            "Code Coverage Report",
            "=" * 80,
            "",
            "Overall Coverage:",
            f"  Lines:    {report.line_percent:.2f}% ({report.line_covered}/{report.line_total})",
            f"  Branches: {report.branch_percent:.2f}% ({report.branch_covered}/{report.branch_total})",
            f"  Functions: {report.function_percent:.2f}% ({report.function_covered}/{report.function_total})",
            "",
            "-" * 80,
            "Coverage by File:",
            "-" * 80,
        ]

        # 按覆盖率排序
        sorted_files = sorted(
            report.files.items(),
            key=lambda x: x[1].line_percent,
        )

        for file_path, data in sorted_files:
            lines.append(f"  {data.line_coverage_str:20s}  {file_path}")

        lines.extend([
            "",
            "=" * 80,
        ])

        return "\n".join(lines)


# 全局单例
coverage_collector = CoverageCollector()
