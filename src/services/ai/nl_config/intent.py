"""
Intent extraction from natural language

Extracts CI/CD configuration intent from natural language descriptions.
"""
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum


class IntentType(str, Enum):
    """Intent types"""
    BUILD = "build"
    TEST = "test"
    DEPLOY = "deploy"
    CACHE = "cache"
    NOTIFICATION = "notification"
    ENVIRONMENT = "environment"
    UNKNOWN = "unknown"


class BuildSystem(str, Enum):
    """Build system types"""
    CMAKE = "cmake"
    QMAKE = "qmake"
    MAKE = "make"
    NINJA = "ninja"
    AUTO = "auto"


class TestFramework(str, Enum):
    """Test framework types"""
    QT_TEST = "qttest"
    GTEST = "gtest"
    CATCH2 = "catch2"
    BOOST_TEST = "boost"
    AUTO = "auto"


@dataclass
class BuildIntent:
    """Build configuration intent"""
    enabled: bool = True
    build_system: BuildSystem = BuildSystem.AUTO
    build_type: str = "RelWithDebInfo"
    parallel_jobs: int = 4
    enable_ccache: bool = True
    cmake_options: Dict[str, Any] = None
    qmake_options: Dict[str, Any] = None
    env_vars: Dict[str, str] = None

    def __post_init__(self):
        if self.cmake_options is None:
            self.cmake_options = {}
        if self.qmake_options is None:
            self.qmake_options = {}
        if self.env_vars is None:
            self.env_vars = {}


@dataclass
class TestIntent:
    """Test configuration intent"""
    enabled: bool = True
    framework: TestFramework = TestFramework.AUTO
    run_coverage: bool = False
    test_discovery: bool = True
    parallel_execution: bool = True
    test_timeout: int = 300
    env_vars: Dict[str, str] = None

    def __post_init__(self):
        if self.env_vars is None:
            self.env_vars = {}


@dataclass
class DeployIntent:
    """Deploy configuration intent"""
    enabled: bool = False
    environments: List[str] = None
    deployment_type: str = "manual"  # manual, auto, rollback
    create_artifacts: bool = True
    artifact_paths: List[str] = None

    def __post_init__(self):
        if self.environments is None:
            self.environments = []
        if self.artifact_paths is None:
            self.artifact_paths = []


@dataclass
class CacheIntent:
    """Cache configuration intent"""
    enabled: bool = True
    cache_paths: List[str] = None
    cache_key: str = "files"
    fallback_keys: List[str] = None

    def __post_init__(self):
        if self.cache_paths is None:
            self.cache_paths = [".ccache", "build"]
        if self.fallback_keys is None:
            self.fallback_keys = []


@dataclass
class NotificationIntent:
    """Notification configuration intent"""
    enabled: bool = False
    on_success: bool = True
    on_failure: bool = True
    channels: List[str] = None  # email, slack, webhook

    def __post_init__(self):
        if self.channels is None:
            self.channels = []


@dataclass
class EnvironmentIntent:
    """Environment configuration intent"""
    variables: Dict[str, str] = None
    docker_enabled: bool = False
    docker_image: str = None
    services: List[str] = None  # postgresql, redis, etc.

    def __post_init__(self):
        if self.variables is None:
            self.variables = {}
        if self.services is None:
            self.services = []


@dataclass
class ExtractedIntent:
    """Complete extracted intent"""
    raw_text: str
    build: BuildIntent
    test: TestIntent
    deploy: DeployIntent
    cache: CacheIntent
    notification: NotificationIntent
    environment: EnvironmentIntent


class IntentExtractor:
    """Extract CI/CD intent from natural language"""

    # Build system keywords
    BUILD_SYSTEM_PATTERNS = {
        BuildSystem.CMAKE: [r"cmake", r"cmakelist", r"CMakeLists"],
        BuildSystem.QMAKE: [r"qmake", r"\.pro", r"qt.*project"],
        BuildSystem.MAKE: [r"makefile", r"make"],
        BuildSystem.NINJA: [r"ninja", r"build\.ninja"],
    }

    # Test framework keywords
    TEST_FRAMEWORK_PATTERNS = {
        TestFramework.QT_TEST: [r"qt.*test", r"qtest", r"qttestlib"],
        TestFramework.GTEST: [r"gtest", r"google.*test", r"googletest"],
        TestFramework.CATCH2: [r"catch2", r"catch"],
        TestFramework.BOOST_TEST: [r"boost.*test", r"boost\.test"],
    }

    # Build type patterns
    BUILD_TYPE_PATTERNS = {
        "Debug": [r"debug", r"dbg"],
        "Release": [r"release", r"rel"],
        "RelWithDebInfo": [r"relwithdebinfo", r"release.*debug"],
        "MinSizeRel": [r"minsizerel", r"min.*size"],
    }

    def extract(self, text: str) -> ExtractedIntent:
        """
        Extract intent from natural language text

        Args:
            text: Natural language description

        Returns:
            ExtractedIntent containing all detected intents
        """
        text_lower = text.lower()

        return ExtractedIntent(
            raw_text=text,
            build=self._extract_build_intent(text_lower),
            test=self._extract_test_intent(text_lower),
            deploy=self._extract_deploy_intent(text_lower),
            cache=self._extract_cache_intent(text_lower),
            notification=self._extract_notification_intent(text_lower),
            environment=self._extract_environment_intent(text_lower),
        )

    def _extract_build_intent(self, text: str) -> BuildIntent:
        """Extract build configuration intent"""
        # Check if build is mentioned
        build_keywords = ["build", "compile", "构建", "编译"]
        enabled = any(keyword in text for keyword in build_keywords)

        if not enabled:
            return BuildIntent(enabled=False)

        # Detect build system
        build_system = self._detect_build_system(text)

        # Detect build type
        build_type = self._detect_build_type(text)

        # Detect parallel jobs
        parallel_jobs = self._extract_number(text, ["parallel", "并行", "并发"], default=4)

        # Detect ccache
        enable_ccache = self._detect_bool(text, ["ccache", "cache"], default=True)

        return BuildIntent(
            enabled=enabled,
            build_system=build_system,
            build_type=build_type,
            parallel_jobs=parallel_jobs,
            enable_ccache=enable_ccache,
        )

    def _extract_test_intent(self, text: str) -> TestIntent:
        """Extract test configuration intent"""
        # Check if testing is mentioned
        test_keywords = ["test", "testing", "测试", "单元测试"]
        enabled = any(keyword in text for keyword in test_keywords)

        if not enabled:
            return TestIntent(enabled=False)

        # Detect test framework
        framework = self._detect_test_framework(text)

        # Detect coverage
        run_coverage = self._detect_bool(text, ["coverage", "gcov", "覆盖率", "代码覆盖"])

        # Detect parallel execution
        parallel_execution = self._detect_bool(text, ["parallel", "concurrent", "并行", "并发"], default=True)

        # Extract timeout
        test_timeout = self._extract_number(text, ["timeout", "超时"], default=300)

        return TestIntent(
            enabled=enabled,
            framework=framework,
            run_coverage=run_coverage,
            test_discovery=True,
            parallel_execution=parallel_execution,
            test_timeout=test_timeout,
        )

    def _extract_deploy_intent(self, text: str) -> DeployIntent:
        """Extract deployment configuration intent"""
        # Check if deployment is mentioned
        deploy_keywords = ["deploy", "deployment", "release", "发布", "部署"]
        enabled = any(keyword in text for keyword in deploy_keywords)

        if not enabled:
            return DeployIntent(enabled=False)

        # Detect environments
        environments = []
        if re.search(r"dev|development|开发", text):
            environments.append("dev")
        if re.search(r"test|testing|测试", text):
            environments.append("test")
        if re.search(r"stag|staging|预发布", text):
            environments.append("staging")
        if re.search(r"prod|production|生产", text):
            environments.append("production")

        # Detect deployment type
        if re.search(r"auto|自动", text):
            deployment_type = "auto"
        elif re.search(r"rollback|回滚", text):
            deployment_type = "rollback"
        else:
            deployment_type = "manual"

        # Detect artifacts
        create_artifacts = self._detect_bool(text, ["artifact", "产物", "构建产物"], default=True)

        return DeployIntent(
            enabled=enabled,
            environments=environments or ["production"],
            deployment_type=deployment_type,
            create_artifacts=create_artifacts,
        )

    def _extract_cache_intent(self, text: str) -> CacheIntent:
        """Extract cache configuration intent"""
        # Check if caching is mentioned
        cache_keywords = ["cache", "ccache", "缓存"]
        enabled = any(keyword in text for keyword in cache_keywords)

        # Default cache paths
        cache_paths = [".ccache", "build"]

        # Detect custom cache paths
        path_match = re.search(r"cache.*?[:\s]+([^,;\n]+)", text)
        if path_match:
            custom_path = path_match.group(1).strip()
            if custom_path:
                cache_paths.append(custom_path)

        return CacheIntent(
            enabled=enabled,
            cache_paths=cache_paths,
            cache_key="files",
            fallback_keys=[],
        )

    def _extract_notification_intent(self, text: str) -> NotificationIntent:
        """Extract notification configuration intent"""
        # Check if notifications are mentioned
        notif_keywords = ["notify", "notification", "alert", "通知", "告警"]
        enabled = any(keyword in text for keyword in notif_keywords)

        if not enabled:
            return NotificationIntent(enabled=False)

        # Detect when to notify
        on_success = self._detect_bool(text, ["success", "成功"], default=True)
        on_failure = self._detect_bool(text, ["failure", "fail", "失败"], default=True)

        # Detect channels
        channels = []
        if re.search(r"email|邮件", text):
            channels.append("email")
        if re.search(r"slack", text, re.IGNORECASE):
            channels.append("slack")
        if re.search(r"webhook", text, re.IGNORECASE):
            channels.append("webhook")

        return NotificationIntent(
            enabled=enabled,
            on_success=on_success,
            on_failure=on_failure,
            channels=channels,
        )

    def _extract_environment_intent(self, text: str) -> EnvironmentIntent:
        """Extract environment configuration intent"""
        # Extract environment variables
        env_vars = {}
        env_pattern = r"([A-Z_]+)\s*[:=]\s*([^\s,;]+)"
        for match in re.finditer(env_pattern, text, re.IGNORECASE):
            var_name = match.group(1).upper()
            var_value = match.group(2)
            env_vars[var_name] = var_value

        # Detect Docker
        docker_enabled = self._detect_bool(text, ["docker", "container", "容器"])
        docker_image = None
        if docker_enabled:
            image_match = re.search(r"(?:docker|image|镜像)[:\s]+([^\s,;]+)", text)
            if image_match:
                docker_image = image_match.group(1)

        # Detect services
        services = []
        if re.search(r"postgres|postgresql|数据库", text, re.IGNORECASE):
            services.append("postgresql")
        if re.search(r"redis", text, re.IGNORECASE):
            services.append("redis")
        if re.search(r"mysql", text, re.IGNORECASE):
            services.append("mysql")
        if re.search(r"rabbitmq|mq", text, re.IGNORECASE):
            services.append("rabbitmq")

        return EnvironmentIntent(
            variables=env_vars,
            docker_enabled=docker_enabled,
            docker_image=docker_image,
            services=services,
        )

    def _detect_build_system(self, text: str) -> BuildSystem:
        """Detect build system from text"""
        for system, patterns in self.BUILD_SYSTEM_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return system
        return BuildSystem.AUTO

    def _detect_test_framework(self, text: str) -> TestFramework:
        """Detect test framework from text"""
        for framework, patterns in self.TEST_FRAMEWORK_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return framework
        return TestFramework.AUTO

    def _detect_build_type(self, text: str) -> str:
        """Detect build type from text"""
        for build_type, patterns in self.BUILD_TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    return build_type
        return "RelWithDebInfo"

    def _detect_bool(self, text: str, keywords: List[str], default: bool = False) -> bool:
        """Detect boolean intent from text"""
        # Check for positive indicators
        positive_words = ["enable", "enabled", "yes", "true", "是", "启用", "开启"]
        negative_words = ["disable", "disabled", "no", "false", "否", "禁用", "关闭"]

        # Check keywords with modifiers
        for keyword in keywords:
            # Positive context
            for pos_word in positive_words:
                if re.search(rf"{pos_word}.*{keyword}|{keyword}.*{pos_word}", text, re.IGNORECASE):
                    return True

            # Negative context
            for neg_word in negative_words:
                if re.search(rf"{neg_word}.*{keyword}|{keyword}.*{neg_word}", text, re.IGNORECASE):
                    return False

        # Default to True if keyword is present
        for keyword in keywords:
            if re.search(keyword, text, re.IGNORECASE):
                return True

        return default

    def _extract_number(self, text: str, keywords: List[str], default: int = 1) -> int:
        """Extract number associated with keywords"""
        for keyword in keywords:
            # Try pattern: "keyword: number" or "keyword = number"
            pattern = rf"{keyword}[:\s=]+(\d+)"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))

            # Try pattern: "number keyword"
            pattern = rf"(\d+)\s*{keyword}"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))

        return default
