"""
静态代码分析器集成

集成Clang-Tidy和Cppcheck
"""

import os
import asyncio
import json
import re
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

from ....utils.logger import get_logger

logger = get_logger(__name__)


class Severity(str, Enum):
    """问题严重程度"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    STYLE = "style"


@dataclass
class CodeIssue:
    """代码问题"""
    tool: str  # clang-tidy, cppcheck
    file_path: str
    line: int
    column: int
    
    severity: Severity
    message: str
    category: str
    rule_id: str
    
    # 建议的修复
    suggestion: Optional[str] = None
    
    # AI判断
    is_false_positive: bool = False
    confidence: float = 1.0  # 0.0 - 1.0


class ClangTidyAnalyzer:
    """Clang-Tidy分析器"""
    
    def __init__(self):
        self.tool_path = "clang-tidy"
    
    async def analyze(
        self,
        source_file: str,
        build_dir: str,
        checks: str = "-*",  # 默认禁用所有检查
        extra_args: List[str] = None,
    ) -> List[CodeIssue]:
        """
        运行Clang-Tidy分析
        
        Args:
            source_file: 源文件路径
            build_dir: 构建目录（用于compile_commands.json）
            checks: 启用的检查列表（例如：'clang-analyzer-*,modernize-*'）
            extra_args: 额外的参数
            
        Returns:
            代码问题列表
        """
        cmd = [
            self.tool_path,
            source_file,
            f"--checks={checks}",
            "-p", build_dir,
        ]
        
        if extra_args:
            cmd.extend(extra_args)
        
        logger.info(
            "clang_tidy_started",
            file=source_file,
            checks=checks,
        )
        
        try:
            result = await self._run_command(
                cmd,
                cwd=build_dir,
                timeout=300,
            )
            
            issues = self._parse_output(result.stdout, result.stderr)
            
            logger.info(
                "clang_tidy_completed",
                file=source_file,
                issues_found=len(issues),
            )
            
            return issues
            
        except Exception as e:
            logger.error(
                "clang_tidy_failed",
                file=source_file,
                error=str(e),
            )
            return []
    
    def _parse_output(self, stdout: str, stderr: str) -> List[CodeIssue]:
        """
        解析Clang-Tidy输出
        
        输出格式：
        file.cpp:10:5: warning: use auto when declaring iterators [modernize-use-auto]
        """
        issues = []
        
        # Clang-Tidy输出格式正则
        pattern = re.compile(
            r'^([^:]+):(\d+):(\d+):\s+(warning|error|info|style):\s+([^\[]+)\s+\[([^\]]+)\]'
        )
        
        output = stdout + "\n" + stderr
        for line in output.splitlines():
            match = pattern.match(line.strip())
            if match:
                file_path, line_num, col, severity, message, rule_id = match.groups()
                
                issues.append(CodeIssue(
                    tool="clang-tidy",
                    file_path=file_path,
                    line=int(line_num),
                    column=int(col),
                    severity=Severity(severity),
                    message=message.strip(),
                    category=self._categorize_rule(rule_id),
                    rule_id=rule_id,
                ))
        
        return issues
    
    def _categorize_rule(self, rule_id: str) -> str:
        """将规则ID分类"""
        if rule_id.startswith("modernize-"):
            return "modernization"
        elif rule_id.startswith("clang-analyzer-"):
            return "security"
        elif rule_id.startswith("readability-"):
            return "readability"
        elif rule_id.startswith("performance-"):
            return "performance"
        elif rule_id.startswith("bugprone-"):
            return "bug-prone"
        elif rule_id.startswith("cppcoreguidelines-"):
            return "core-guidelines"
        else:
            return "general"
    
    async def _run_command(self, cmd: List[str], cwd: str, timeout: int = 300):
        """运行命令"""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise
        
        return type('Result', (), {
            'returncode': process.returncode,
            'stdout': stdout.decode('utf-8', errors='replace'),
            'stderr': stderr.decode('utf-8', errors='replace'),
        })()


class CppcheckAnalyzer:
    """Cppcheck分析器"""
    
    def __init__(self):
        self.tool_path = "cppcheck"
    
    async def analyze(
        self,
        source_dir: str,
        enabled_checks: List[str] = None,
        suppressions: List[str] = None,
    ) -> List[CodeIssue]:
        """
        运行Cppcheck分析
        
        Args:
            source_dir: 源代码目录
            enabled_checks: 启用的检查类别
            suppressions: 抑制的错误ID
            
        Returns:
            代码问题列表
        """
        cmd = [
            self.tool_path,
            source_dir,
            "--enable=all",
            "--xml",
            "--xml-version=2",
        ]
        
        if suppressions:
            for supp in suppressions:
                cmd.append(f"--suppress={supp}")
        
        logger.info(
            "cppcheck_started",
            source_dir=source_dir,
        )
        
        try:
            result = await self._run_command(
                cmd,
                cwd=source_dir,
                timeout=600,  # Cppcheck可能需要更长时间
            )
            
            issues = self._parse_xml_output(result.stdout)
            
            logger.info(
                "cppcheck_completed",
                source_dir=source_dir,
                issues_found=len(issues),
            )
            
            return issues
            
        except Exception as e:
            logger.error(
                "cppcheck_failed",
                source_dir=source_dir,
                error=str(e),
            )
            return []
    
    def _parse_xml_output(self, xml_output: str) -> List[CodeIssue]:
        """
        解析Cppcheck XML输出
        
        XML格式：
        <?xml version="1.0" encoding="UTF-8"?>
        <results version="2">
          <errors>
            <error id="memoryLeak" severity="error" msg="Memory leak...">
              <location file="file.cpp" line="10"/>
            </error>
          </errors>
        </results>
        """
        issues = []
        
        try:
            import xml.etree.ElementTree as ET
            
            root = ET.fromstring(xml_output)
            
            for error in root.findall(".//error"):
                error_id = error.get("id", "")
                severity = error.get("severity", "error")
                message = error.get("msg", "")
                
                location = error.find("location")
                if location is not None:
                    file_path = location.get("file", "")
                    line = int(location.get("line", "0"))
                else:
                    continue
                
                issues.append(CodeIssue(
                    tool="cppcheck",
                    file_path=file_path,
                    line=line,
                    column=0,
                    severity=Severity(severity),
                    message=message,
                    category=self._categorize_error(error_id),
                    rule_id=error_id,
                ))
        
        except Exception as e:
            logger.error(
                "cppcheck_xml_parse_failed",
                error=str(e),
            )
        
        return issues
    
    def _categorize_error(self, error_id: str) -> str:
        """将错误ID分类"""
        if "memory" in error_id.lower():
            return "memory"
        elif "buffer" in error_id.lower():
            return "buffer"
        elif "unused" in error_id.lower():
            return "unused"
        elif "nullPointer" in error_id:
            return "null-pointer"
        else:
            return "general"
    
    async def _run_command(self, cmd: List[str], cwd: str, timeout: int = 600):
        """运行命令"""
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise
        
        return type('Result', (), {
            'returncode': process.returncode,
            'stdout': stdout.decode('utf-8', errors='replace'),
            'stderr': stderr.decode('utf-8', errors='replace'),
        })()
