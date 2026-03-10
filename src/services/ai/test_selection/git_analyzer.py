"""
Git变更分析器

分析Git提交的变更内容
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from enum import Enum


class ChangeType(str, Enum):
    """变更类型"""
    ADDED = "added"
    MODIFIED = "modified"
    DELETED = "deleted"
    RENAMED = "renamed"


@dataclass
class FileChange:
    """文件变更"""
    path: str
    change_type: ChangeType
    
    # Git diff信息
    old_path: Optional[str] = None
    additions: int = 0
    deletions: int = 0
    
    # 解析后的内容
    added_functions: Set[str] = None
    modified_functions: Set[str] = None
    deleted_functions: Set[str] = None
    
    def __post_init__(self):
        if self.added_functions is None:
            self.added_functions = set()
        if self.modified_functions is None:
            self.modified_functions = set()
        if self.deleted_functions is None:
            self.deleted_functions = set()


@dataclass
class CommitChange:
    """提交变更"""
    sha: str
    author: str
    message: str
    files: List[FileChange]
    
    # 摘要
    total_files: int = 0
    total_additions: int = 0
    total_deletions: int = 0


class GitAnalyzer:
    """Git变更分析器"""
    
    def __init__(self):
        self.repo_path: Optional[str] = None
    
    def analyze_diff(
        self,
        repo_path: str,
        base_ref: str,
        head_ref: str,
    ) -> List[CommitChange]:
        """
        分析Git diff
        
        Args:
            repo_path: 仓库路径
            base_ref: 基准引用（分支、标签或commit）
            head_ref: 头部引用
            
        Returns:
            提交变更列表
        """
        self.repo_path = repo_path
        changes = []
        
        # 获取提交列表
        commits = self._get_commits(base_ref, head_ref)
        
        # 分析每个提交
        for commit in commits:
            files = self._get_files_changed(commit['sha'])
            change = CommitChange(
                sha=commit['sha'],
                author=commit.get('author', {}).get('name', ''),
                message=commit.get('message', ''),
                files=files,
            )
            
            # 计算统计
            change.total_files = len(files)
            change.total_additions = sum(f.additions for f in files)
            change.total_deletions = sum(f.deletions for f in files)
            
            changes.append(change)
        
        return changes
    
    def analyze_mr_changes(
        self,
        repo_path: str,
        source_branch: str,
        target_branch: str,
    ) -> List[FileChange]:
        """
        分析MR的变更
        
        Args:
            repo_path: 仓库路径
            source_branch: 源分支
            target_branch: 目标分支
            
        Returns:
            文件变更列表
        """
        self.repo_path = repo_path
        
        # 获取diff的文件列表
        files = self._get_files_changed_between_branches(
            source_branch,
            target_branch,
        )
        
        # 解析函数级变更
        for file_change in files:
            if file_change.change_type in [ChangeType.MODIFIED, ChangeType.ADDED]:
                self._parse_function_changes(file_change)
        
        return files
    
    def _get_commits(self, base_ref: str, head_ref: str) -> List[dict]:
        """获取提交列表"""
        import subprocess
        
        cmd = [
            "git",
            "log",
            f"{base_ref}..{head_ref}",
            "--format=%H|%an|%s",
        ]
        
        result = subprocess.run(
            cmd,
            cwd=self.repo_path,
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            return []
        
        commits = []
        for line in result.stdout.strip().splitlines():
            parts = line.split('|')
            if len(parts) == 3:
                commits.append({
                    'sha': parts[0],
                    'author': {'name': parts[1]},
                    'message': parts[2],
                })
        
        return commits
    
    def _get_files_changed(self, commit_sha: str) -> List[FileChange]:
        """获取提交的文件变更"""
        import subprocess
        
        cmd = [
            "git",
            "show",
            "--format=",
            "--name-status",
            commit_sha,
        ]
        
        result = subprocess.run(
            cmd,
            cwd=self.repo_path,
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            return []
        
        files = []
        for line in result.stdout.strip().splitlines():
            if not line:
                continue
            
            parts = line.split('\t')
            status = parts[0]
            path = parts[1] if len(parts) > 1 else ''
            
            change_type = self._parse_status(status)
            
            file_change = FileChange(
                path=path,
                change_type=change_type,
                old_path=parts[2] if len(parts) > 2 else None,
            )
            
            # 获取文件diff统计
            file_change.additions, file_change.deletions = \
                self._get_file_diff_stats(commit_sha, path)
            
            files.append(file_change)
        
        return files
    
    def _get_files_changed_between_branches(
        self,
        source_branch: str,
        target_branch: str,
    ) -> List[FileChange]:
        """获取分支间的文件变更"""
        import subprocess
        
        cmd = [
            "git",
            "diff",
            "--name-status",
            f"{target_branch}...{source_branch}",
        ]
        
        result = subprocess.run(
            cmd,
            cwd=self.repo_path,
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            return []
        
        files = []
        for line in result.stdout.strip().splitlines():
            if not line:
                continue
            
            parts = line.split('\t')
            status = parts[0]
            path = parts[1] if len(parts) > 1 else ''
            
            change_type = self._parse_status(status)
            
            file_change = FileChange(
                path=path,
                change_type=change_type,
                old_path=parts[2] if len(parts) > 2 else None,
            )
            
            files.append(file_change)
        
        return files
    
    def _get_file_diff_stats(self, commit_sha: str, path: str) -> tuple[int, int]:
        """获取文件diff统计"""
        import subprocess
        
        cmd = [
            "git",
            "show",
            f"{commit_sha}:{path}",
        ]
        
        result = subprocess.run(
            cmd,
            cwd=self.repo_path,
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            return 0, 0
        
        # 简单的行数统计（更准确的方法是使用git diff --numstat）
        lines = result.stdout.splitlines()
        return len(lines), 0
    
    def _parse_status(self, status: str) -> ChangeType:
        """解析Git状态"""
        status_char = status[0] if status else 'M'
        
        status_map = {
            'A': ChangeType.ADDED,
            'M': ChangeType.MODIFIED,
            'D': ChangeType.DELETED,
            'R': ChangeType.RENAMED,
        }
        
        return status_map.get(status_char, ChangeType.MODIFIED)
    
    def _parse_function_changes(self, file_change: FileChange):
        """
        解析函数级变更
        
        使用简单的正则表达式匹配C/C++函数定义
        """
        file_path = Path(self.repo_path) / file_change.path
        
        if not file_path.exists():
            return
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            return
        
        # C/C++函数正则
        # 匹配：返回类型 函数名(参数)
        function_pattern = re.compile(
            r'^\s*(?:[\w<>*&]+\s+)+(\w+)\s*\([^)]*\)\s*(?:const\s*)?(?:override\s*)?(?:final\s*)?\{',
            re.MULTILINE,
        )
        
        functions = set()
        for match in function_pattern.finditer(content):
            func_name = match.group(1)
            # 过滤掉一些常见的非函数关键字
            if func_name not in ['if', 'for', 'while', 'switch', 'catch']:
                functions.add(func_name)
        
        file_change.modified_functions = functions
