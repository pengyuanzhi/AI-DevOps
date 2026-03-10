"""
依赖图构建器

构建代码依赖关系图
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque


@dataclass
class Node:
    """依赖图节点"""
    id: str  # 可以是文件、类、函数等
    type: str  # file, class, function
    name: str
    path: Optional[str] = None
    
    # 依赖关系
    dependencies: Set[str] = field(default_factory=set)  # 依赖的节点ID
    dependents: Set[str] = field(default_factory=set)  # 被依赖的节点ID


class DependencyGraph:
    """依赖图"""
    
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self._adjacency_list: Dict[str, Set[str]] = defaultdict(set)
    
    def add_node(self, node: Node) -> None:
        """添加节点"""
        self.nodes[node.id] = node
    
    def add_dependency(self, from_id: str, to_id: str) -> None:
        """
        添加依赖关系
        
        Args:
            from_id: 依赖方ID
            to_id: 被依赖方ID
        """
        self._adjacency_list[from_id].add(to_id)
        
        if from_id in self.nodes:
            self.nodes[from_id].dependencies.add(to_id)
        if to_id in self.nodes:
            self.nodes[to_id].dependents.add(from_id)
    
    def get_dependencies(self, node_id: str) -> Set[str]:
        """获取直接依赖"""
        return self._adjacency_list.get(node_id, set())
    
    def get_dependents(self, node_id: str) -> Set[str]:
        """获取直接被依赖"""
        if node_id in self.nodes:
            return self.nodes[node_id].dependents
        return set()
    
    def get_downstream(self, node_id: str, max_depth: int = 10) -> Set[str]:
        """
        获取下游依赖（依赖此节点的所有节点）
        
        Args:
            node_id: 起始节点ID
            max_depth: 最大遍历深度
            
        Returns:
            下游节点ID集合
        """
        visited = set()
        queue = deque([(node_id, 0)])
        
        while queue:
            current, depth = queue.popleft()
            
            if depth >= max_depth:
                continue
            
            if current in visited:
                continue
            
            visited.add(current)
            
            # 获取依赖当前节点的所有节点
            dependents = self.get_dependents(current)
            for dependent in dependents:
                if dependent not in visited:
                    queue.append((dependent, depth + 1))
        
        visited.discard(node_id)  # 移除起始节点
        return visited
    
    def get_upstream(self, node_id: str, max_depth: int = 10) -> Set[str]:
        """
        获取上游依赖（当前节点依赖的所有节点）
        
        Args:
            node_id: 起始节点ID
            max_depth: 最大遍历深度
            
        Returns:
            上游节点ID集合
        """
        visited = set()
        queue = deque([(node_id, 0)])
        
        while queue:
            current, depth = queue.popleft()
            
            if depth >= max_depth:
                continue
            
            if current in visited:
                continue
            
            visited.add(current)
            
            # 获取当前节点依赖的所有节点
            dependencies = self.get_dependencies(current)
            for dependency in dependencies:
                if dependency not in visited:
                    queue.append((dependency, depth + 1))
        
        visited.discard(node_id)  # 移除起始节点
        return visited
    
    def find_path(self, from_id: str, to_id: str) -> Optional[List[str]]:
        """
        查找两个节点之间的路径
        
        Args:
            from_id: 起始节点ID
            to_id: 目标节点ID
            
        Returns:
            路径节点列表或None
        """
        if from_id == to_id:
            return [from_id]
        
        # BFS查找路径
        queue = deque([(from_id, [from_id])])
        visited = set([from_id])
        
        while queue:
            current, path = queue.popleft()
            
            # 检查下游
            for neighbor in self.get_dependents(current):
                if neighbor == to_id:
                    return path + [neighbor]
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return None
    
    def get_stats(self) -> dict:
        """获取图统计信息"""
        return {
            "total_nodes": len(self.nodes),
            "total_edges": sum(len(deps) for deps in self._adjacency_list.values()),
            "avg_degree": sum(len(deps) for deps in self._adjacency_list.values()) / max(len(self.nodes), 1),
        }


class DependencyGraphBuilder:
    """依赖图构建器"""
    
    def __init__(self):
        self.graph = DependencyGraph()
    
    def build_from_source(self, source_dir: str) -> DependencyGraph:
        """
        从源代码构建依赖图
        
        Args:
            source_dir: 源代码目录
            
        Returns:
            依赖图
        """
        self.graph = DependencyGraph()
        
        # 遍历所有源文件
        source_path = Path(source_dir)
        
        # 构建文件级依赖
        self._build_file_dependencies(source_path)
        
        # 构建类/函数级依赖
        self._build_function_dependencies(source_path)
        
        return self.graph
    
    def _build_file_dependencies(self, source_path: Path) -> None:
        """构建文件级依赖"""
        cpp_extensions = ['.cpp', '.cc', '.cxx', '.c', '.h', '.hpp', '.hxx']
        
        for source_file in source_path.rglob('*'):
            if not source_file.is_file():
                continue
            
            if source_file.suffix not in cpp_extensions:
                continue
            
            # 添加文件节点
            file_id = f"file:{source_file.relative_to(source_path)}"
            node = Node(
                id=file_id,
                type="file",
                name=source_file.name,
                path=str(source_file),
            )
            self.graph.add_node(node)
            
            # 解析#include依赖
            try:
                content = source_file.read_text(encoding='utf-8', errors='ignore')
                includes = self._parse_includes(content)
                
                for include in includes:
                    include_id = f"file:{include}"
                    self.graph.add_dependency(file_id, include_id)
                    
            except Exception:
                pass
    
    def _build_function_dependencies(self, source_path: Path) -> None:
        """构建函数级依赖"""
        cpp_extensions = ['.cpp', '.cc', '.cxx', '.c']
        
        for source_file in source_path.rglob('*'):
            if not source_file.is_file():
                continue
            
            if source_file.suffix not in cpp_extensions:
                continue
            
            try:
                content = source_file.read_text(encoding='utf-8', errors='ignore')
                
                # 解析函数定义
                functions = self._parse_functions(content, source_file.name)
                
                # 解析函数调用
                for func_name, func_node in functions.items():
                    calls = self._parse_function_calls(content, func_name)
                    
                    for called_func in calls:
                        called_id = f"function:{called_func}"
                        self.graph.add_dependency(func_node.id, called_id)
                
            except Exception:
                pass
    
    def _parse_includes(self, content: str) -> List[str]:
        """解析#include指令"""
        includes = []
        
        # 匹配 #include "xxx.h" 和 #include <xxx.h>
        include_pattern = re.compile(r'#include\s+[<"]([^>"]+)[>"]')
        
        for match in include_pattern.finditer(content):
            includes.append(match.group(1))
        
        return includes
    
    def _parse_functions(self, content: str, file_name: str) -> Dict[str, Node]:
        """解析函数定义"""
        functions = {}
        
        # C/C++函数定义正则
        function_pattern = re.compile(
            r'^\s*(?:[\w<>*&]+\s+)+(\w+)\s*\([^)]*\)\s*(?:const\s*)?(?:override\s*)?(?:final\s*)?\{',
            re.MULTILINE,
        )
        
        for match in function_pattern.finditer(content):
            func_name = match.group(1)
            
            # 过滤关键字
            if func_name not in ['if', 'for', 'while', 'switch', 'catch']:
                func_id = f"function:{file_name}:{func_name}"
                node = Node(
                    id=func_id,
                    type="function",
                    name=func_name,
                )
                functions[func_name] = node
                self.graph.add_node(node)
        
        return functions
    
    def _parse_function_calls(self, content: str, function_name: str) -> Set[str]:
        """解析函数调用"""
        calls = set()
        
        # 函数调用正则（简化版）
        # 匹配 function_name(...)
        call_pattern = re.compile(r'(\w+)\s*\(')
        
        # 找到函数定义的位置
        func_start = content.find(function_name)
        if func_start == -1:
            return calls
        
        # 找到函数体
        brace_start = content.find('{', func_start)
        if brace_start == -1:
            return calls
        
        # 找到匹配的}
        brace_count = 0
        func_end = brace_start
        for i in range(brace_start, len(content)):
            if content[i] == '{':
                brace_count += 1
            elif content[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    func_end = i
                    break
        
        if func_end > brace_start:
            func_body = content[brace_start:func_end]
            
            for match in call_pattern.finditer(func_body):
                called = match.group(1)
                # 过滤一些常见的关键字和类型转换
                if called not in ['if', 'for', 'while', 'switch', 'catch', 'sizeof']:
                    calls.add(called)
        
        return calls
