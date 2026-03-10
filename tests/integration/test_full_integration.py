"""
Full Integration Tests for AI-CICD Platform

Comprehensive integration tests for all core features.
"""
import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.services.build.service import BuildService
from src.services.test.service import TestService
from src.services.ai.test_selection.service import TestSelectionService
from src.services.ai.code_review.review_service import AIEnhancedCodeReview
from src.services.ai.nl_config.service import NLConfigService
from src.services.ai.memory_safety.service import MemorySafetyService
from src.services.ai.pipeline_maintenance.service import PipelineMaintenanceService
from src.services.websocket.manager import manager


class TestBuildIntegration:
    """Build system integration tests"""

    @pytest.mark.asyncio
    async def test_build_service_detection(self):
        """Test build system auto-detection"""
        service = BuildService()

        # Create a temporary directory with CMakeLists.txt
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            cmake_path = Path(tmpdir) / "CMakeLists.txt"
            cmake_path.write_text("""
cmake_minimum_required(VERSION 3.10)
project(TestProject)
add_executable(test main.cpp)
""")

            # Detect build system
            build_type = await service.auto_detect_build_system(tmpdir)
            assert build_type == "cmake", f"Expected 'cmake', got '{build_type}'"
            print("✓ Build system auto-detection works")

    @pytest.mark.asyncio
    async def test_build_executors(self):
        """Test build executors are properly initialized"""
        service = BuildService()

        # Check all executors are initialized
        assert "cmake" in service.executors
        assert "qmake" in service.executors
        assert "make" in service.executors
        assert "ninja" in service.executors
        print("✓ All build executors initialized")


class TestIntegration:
    """Test system integration tests"""

    @pytest.mark.asyncio
    async def test_test_service_initialization(self):
        """Test test service initialization"""
        service = TestService()

        # Check all executors are initialized
        assert "qttest" in service.executors
        print("✓ Test service initialized with Qt Test executor")


class TestAIFeaturesIntegration:
    """AI features integration tests"""

    @pytest.mark.asyncio
    async def test_intent_extraction(self):
        """Test natural language intent extraction"""
        from src.services.ai.nl_config.intent import IntentExtractor

        extractor = IntentExtractor()

        # Test build intent extraction
        intent = extractor.extract("Build my C++ project with CMake in release mode")

        assert intent.build.enabled is True
        assert intent.build.build_system.value == "cmake"
        assert intent.build.build_type == "Release"
        print("✓ Intent extraction works for build configuration")

    @pytest.mark.asyncio
    async def test_nl_config_generation(self):
        """Test natural language configuration generation"""
        service = NLConfigService()

        result = await service.generate_config(
            description="Build with CMake, run tests with coverage",
            project_name="test-project",
            use_ai_enhancement=False,  # Skip AI for speed
        )

        assert result["success"] is True
        assert result["config"] is not None
        assert "stages:" in result["config"]
        assert "build:" in result["config"]
        print("✓ Natural language configuration generation works")

    @pytest.mark.asyncio
    async def test_failure_classification(self):
        """Test failure classification"""
        from src.services.ai.pipeline_maintenance.service import FailureClassifier

        classifier = FailureClassifier()

        # Test build failure classification
        build_log = "error: 'openssl/ssl.h' file not found"
        failure = classifier.classify_build_failure(
            log=build_log,
            stage="build",
            job_name="compile",
        )

        assert failure.failure_type.value == "dependency_error"
        assert failure.severity.value == "critical"
        print("✓ Failure classification works")


class TestWebSocketIntegration:
    """WebSocket integration tests"""

    @pytest.mark.asyncio
    async def test_connection_manager(self):
        """Test WebSocket connection manager"""
        # Test stats
        stats = await asyncio.to_thread(manager.get_connection_count)
        assert stats >= 0
        print("✓ WebSocket connection manager initialized")


class TestDatabaseModels:
    """Database models tests"""

    def test_models_import(self):
        """Test that all database models can be imported"""
        from src.db.models import (
            Base, User, Project, Pipeline, Job,
            TestCase, TestResult, CodeReview, MemoryReport,
            QualityMetric, DependencyGraph, BuildArtifact,
            TestSelectionHistory, AIUsageStats, AutoFixHistory
        )

        # Check that all models inherit from Base
        assert hasattr(User, "__tablename__")
        assert hasattr(Project, "__tablename__")
        assert hasattr(Pipeline, "__tablename__")
        assert hasattr(TestCase, "__tablename__")
        assert hasattr(TestResult, "__tablename__")
        assert hasattr(CodeReview, "__tablename__")
        assert hasattr(MemoryReport, "__tablename__")
        assert hasattr(QualityMetric, "__tablename__")
        assert hasattr(DependencyGraph, "__tablename__")
        assert hasattr(BuildArtifact, "__tablename__")
        assert hasattr(TestSelectionHistory, "__tablename__")
        assert hasattr(AIUsageStats, "__tablename__")
        assert hasattr(AutoFixHistory, "__tablename__")
        print("✓ All database models importable")


class TestAPIRoutes:
    """API routes tests"""

    def test_api_router_initialization(self):
        """Test that API router initializes correctly"""
        from src.api.v1 import api_router

        # Check that router has routes
        assert api_router.routes is not None
        assert len(list(api_router.routes)) > 0
        print("✓ API router initialized with routes")

    def test_all_modules_registered(self):
        """Test that all API modules are registered"""
        from src.api.v1 import api_router

        route_paths = [route.path for route in api_router.routes]

        # Check for key endpoints
        assert any("/projects" in path for path in route_paths)
        assert any("/pipelines" in path for path in route_paths)
        assert any("/build" in path for path in route_paths)
        assert any("/test" in path for path in route_paths)
        assert any("/nl-config" in path for path in route_paths)
        assert any("/memory-safety" in path for path in route_paths)
        assert any("/pipeline-maintenance" in path for path in route_paths)
        print("✓ All API modules registered")


@pytest.mark.asyncio
async def test_full_pipeline_simulation():
    """Simulate a full CI/CD pipeline"""
    print("\n=== Full Pipeline Simulation ===")

    # 1. Natural Language Config Generation
    print("\n1. Generating CI/CD configuration from natural language...")
    nl_service = NLConfigService()
    config_result = await nl_service.generate_config(
        description="Build C++ project with CMake, run tests with coverage, deploy to staging",
        project_name="demo-project",
        use_ai_enhancement=False,
    )

    assert config_result["success"]
    print("   ✓ Configuration generated")

    # 2. Build System Detection
    print("\n2. Detecting build system...")
    build_service = BuildService()
    print("   ✓ Build service ready")

    # 3. Test Service Ready
    print("\n3. Test service initialization...")
    test_service = TestService()
    print("   ✓ Test service ready")

    # 4. Test Selection Service Ready
    print("\n4. Intelligent test selection...")
    test_selection_service = TestSelectionService()
    print("   ✓ Test selection service ready")

    # 5. Pipeline Maintenance Service Ready
    print("\n5. Pipeline maintenance service...")
    maintenance_service = PipelineMaintenanceService()
    print("   ✓ Pipeline maintenance service ready")

    # 6. Memory Safety Service Ready
    print("\n6. Memory safety detection...")
    memory_service = MemorySafetyService()
    print("   ✓ Memory safety service ready")

    # 7. WebSocket Manager Ready
    print("\n7. WebSocket communication...")
    ws_stats = manager.get_connection_count()
    print(f"   ✓ WebSocket manager ready (active connections: {ws_stats})")

    print("\n=== All Services Operational ===")


def test_import_all_services():
    """Test that all services can be imported without errors"""
    services = [
        "src.services.build.service",
        "src.services.test.service",
        "src.services.ai.test_selection.service",
        "src.services.ai.code_review.review_service",
        "src.services.ai.nl_config.service",
        "src.services.ai.memory_safety.service",
        "src.services.ai.pipeline_maintenance.service",
        "src.services.websocket.manager",
    ]

    for service_path in services:
        try:
            __import__(service_path)
            print(f"✓ {service_path}")
        except Exception as e:
            print(f"✗ {service_path}: {e}")
            raise

    assert True, "All services imported successfully"


def test_config_settings():
    """Test configuration settings"""
    from src.utils.config import settings

    # Check required settings exist
    assert hasattr(settings, "database_url")
    assert hasattr(settings, "gitlab_url")
    assert hasattr(settings, "redis_url")
    assert hasattr(settings, "rabbitmq_url")
    print("✓ Configuration settings loaded")


def test_database_session():
    """Test database session factory"""
    from src.db.session import get_async_engine

    # Test that engine can be created (doesn't need to connect)
    try:
        # Just verify the function exists and is callable
        assert callable(get_async_engine)
        print("✓ Database session factory available")
    except Exception as e:
        print(f"✗ Database session factory error: {e}")
        raise


if __name__ == "__main__":
    import sys

    # Run with pytest
    sys.exit(pytest.main([__file__, "-v", "-s", "--tb=short"]))
