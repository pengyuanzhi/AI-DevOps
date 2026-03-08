"""CI/CD 配置模板管理器."""

from pathlib import Path
from typing import List, Optional

from src.models.cicd import Template
from src.utils.logger import get_logger

logger = get_logger(__name__)


class TemplateManager:
    """CI/CD 配置模板管理器.

    管理内置的 CI/CD 配置模板，支持根据项目类型和需求选择合适的模板。
    """

    def __init__(self):
        """初始化模板管理器."""
        self.templates: dict[str, Template] = {}
        self._load_builtin_templates()

    def _load_builtin_templates(self):
        """加载内置模板."""
        logger.info("loading_builtin_templates")

        # C++ CMake + Google Test 模板
        self.templates["cpp-cmake-gtest"] = Template(
            id="cpp-cmake-gtest",
            name="C++ CMake + Google Test",
            description="标准 C++ 项目配置，使用 CMake 构建和 Google Test 测试框架",
            category="cpp",
            project_types=["cpp"],
            build_systems=["cmake"],
            test_frameworks=["gtest"],
            tags=["cpp", "cmake", "gtest", "ccache"],
            estimated_build_time="5-10分钟",
            complexity="medium",
            default_optimizations=["ccache", "parallel_build", "artifacts_cache"],
            content=self._get_cpp_cmake_gtest_template(),
        )

        # C++ Makefile + Google Test 模板
        self.templates["cpp-make-gtest"] = Template(
            id="cpp-make-gtest",
            name="C++ Makefile + Google Test",
            description="使用 Makefile 的 C++ 项目配置",
            category="cpp",
            project_types=["cpp"],
            build_systems=["make"],
            test_frameworks=["gtest"],
            tags=["cpp", "make", "gtest"],
            estimated_build_time="3-8分钟",
            complexity="simple",
            default_optimizations=["ccache", "parallel_build"],
            content=self._get_cpp_make_gtest_template(),
        )

        # QT Widgets 项目模板
        self.templates["qt-widgets-cmake"] = Template(
            id="qt-widgets-cmake",
            name="QT Widgets + CMake",
            description="QT GUI 应用配置，使用 CMake 构建",
            category="qt",
            project_types=["qt"],
            build_systems=["cmake"],
            test_frameworks=["qtest"],
            tags=["qt", "cmake", "gui", "qtest"],
            estimated_build_time="8-15分钟",
            complexity="complex",
            requires_docker=True,
            default_optimizations=["ccache", "parallel_build", "qt_cache"],
            content=self._get_qt_cmake_template(),
        )

        # C++ Catch2 测试框架模板
        self.templates["cpp-cmake-catch2"] = Template(
            id="cpp-cmake-catch2",
            name="C++ CMake + Catch2",
            description="使用 Catch2 测试框架的 C++ 项目配置",
            category="cpp",
            project_types=["cpp"],
            build_systems=["cmake"],
            test_frameworks=["catch2"],
            tags=["cpp", "cmake", "catch2"],
            estimated_build_time="5-10分钟",
            complexity="medium",
            default_optimizations=["ccache", "parallel_build"],
            content=self._get_cpp_cmake_catch2_template(),
        )

        logger.info(
            "builtin_templates_loaded",
            count=len(self.templates),
            template_ids=list(self.templates.keys()),
        )

    def get_template(self, template_id: str) -> Optional[Template]:
        """获取指定模板.

        Args:
            template_id: 模板ID

        Returns:
            模板对象，如果不存在则返回 None
        """
        return self.templates.get(template_id)

    def list_templates(
        self,
        project_type: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[Template]:
        """列出可用模板.

        Args:
            project_type: 项目类型过滤
            category: 分类过滤

        Returns:
            模板列表
        """
        templates = list(self.templates.values())

        if project_type:
            templates = [t for t in templates if project_type in t.project_types]

        if category:
            templates = [t for t in templates if t.category == category]

        return templates

    def find_best_template(
        self,
        project_type: str,
        build_system: Optional[str] = None,
        test_framework: Optional[str] = None,
    ) -> Optional[Template]:
        """查找最匹配的模板.

        Args:
            project_type: 项目类型
            build_system: 构建系统
            test_framework: 测试框架

        Returns:
            最佳匹配的模板，如果没有匹配则返回 None
        """
        # 精确匹配
        for template in self.templates.values():
            if template.matches_requirements(project_type, build_system, test_framework):
                logger.info(
                    "template_exact_match",
                    template_id=template.id,
                    project_type=project_type,
                    build_system=build_system,
                    test_framework=test_framework,
                )
                return template

        # 部分匹配（仅项目类型）
        for template in self.templates.values():
            if project_type in template.project_types:
                logger.info(
                    "template_partial_match",
                    template_id=template.id,
                    project_type=project_type,
                )
                return template

        logger.warning(
            "no_template_found",
            project_type=project_type,
            build_system=build_system,
            test_framework=test_framework,
        )
        return None

    def _get_cpp_cmake_gtest_template(self) -> str:
        """获取 C++ CMake + Google Test 模板内容."""
        return """stages:
  - build
  - test

variables:
  # 使用 ccache 加速构建
  CCACHE_DIR: ${CI_PROJECT_DIR}/.ccache
  CACHE_COMPRESSION_LEVEL: "4"

# 缓存配置
.cache:ccache:
  cache:
    key: ccache-${CI_COMMIT_REF_SLUG}
    paths:
      - .ccache/

.build:script:
  before_script:
    - mkdir -p .ccache
    - cmake -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_CXX_FLAGS="-Wall -Wextra"

build:
  stage: build
  image: gcc:latest
  extends:
    - .cache:ccache
    - .build:script
  script:
    - cmake --build build -- -j$(nproc)
  artifacts:
    paths:
      - build/
    expire_in: 1 hour
  cache:
    key: build-${CI_COMMIT_REF_SLUG}
    paths:
      - build/

test:
  stage: test
  image: gcc:latest
  dependencies:
    - build
  script:
    - cd build
    - ctest --output-on-failure
  artifacts:
    reports:
      junit: build/**/*.xml
"""

    def _get_cpp_make_gtest_template(self) -> str:
        """获取 C++ Makefile + Google Test 模板内容."""
        return """stages:
  - build
  - test

variables:
  CCACHE_DIR: ${CI_PROJECT_DIR}/.ccache

.cache:ccache:
  cache:
    key: ccache-${CI_COMMIT_REF_SLUG}
    paths:
      - .ccache/

build:
  stage: build
  image: gcc:latest
  extends: .cache:ccache
  script:
    - mkdir -p .ccache
    - make -j$(nproc)
  artifacts:
    paths:
      - bin/
      - lib/
    expire_in: 1 hour

test:
  stage: test
  image: gcc:latest
  dependencies:
    - build
  script:
    - make test
"""

    def _get_qt_cmake_template(self) -> str:
        """获取 QT CMake 模板内容."""
        return """stages:
  - build
  - test

variables:
  QT_VERSION: "6.5"
  CCACHE_DIR: ${CI_PROJECT_DIR}/.ccache
  # QT 路径缓存
  Qt6_DIR: "/opt/Qt/${QT_VERSION}/gcc_64/lib/cmake/Qt6"

.cache:ccache:
  cache:
    key: ccache-${CI_COMMIT_REF_SLUG}
    paths:
      - .ccache/

build:
  stage: build
  image: qtbase/qt6:latest
  extends: .cache:ccache
  before_script:
    - mkdir -p .ccache
    - apt-get update -qq
    - apt-get install -y qt6-base-dev qt6-tools-dev cmake
  script:
    - cmake -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_PREFIX_PATH="/opt/Qt/${QT_VERSION}/gcc_64"
    - cmake --build build -- -j$(nproc)
  artifacts:
    paths:
      - build/
    expire_in: 1 hour

test:
  stage: test
  image: qtbase/qt6:latest
  dependencies:
    - build
  script:
    - cd build
    - ctest --output-on-failure
"""

    def _get_cpp_cmake_catch2_template(self) -> str:
        """获取 C++ CMake + Catch2 模板内容."""
        return """stages:
  - build
  - test

variables:
  CCACHE_DIR: ${CI_PROJECT_DIR}/.ccache

.cache:ccache:
  cache:
    key: ccache-${CI_COMMIT_REF_SLUG}
    paths:
      - .ccache/

build:
  stage: build
  image: gcc:latest
  extends: .cache:ccache
  before_script:
    - mkdir -p .ccache
    - cmake -B build -DCMAKE_BUILD_TYPE=Release
  script:
    - cmake --build build -- -j$(nproc)
  artifacts:
    paths:
      - build/
    expire_in: 1 hour

test:
  stage: test
  image: gcc:latest
  dependencies:
    - build
  script:
    - cd build
    - ./tests --use-colour yes --reporter junit
  artifacts:
    reports:
      junit: build/results/*.xml
"""
