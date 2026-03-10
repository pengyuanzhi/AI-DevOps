"""
GitLab CI configuration generator

Generates .gitlab-ci.yml files from extracted intent.
"""
import yaml
from typing import Dict, List, Any, Optional
from .intent import ExtractedIntent, BuildSystem, TestFramework


class GitLabCIGenerator:
    """Generate GitLab CI configuration from intent"""

    def __init__(self):
        self.cache_prefix = "ai-cicd-cache"

    def generate(self, intent: ExtractedIntent, project_name: str = "project") -> str:
        """
        Generate complete GitLab CI configuration

        Args:
            intent: Extracted intent from natural language
            project_name: Name of the project

        Returns:
            YAML configuration string
        """
        config = {
            "image": self._get_base_image(intent),
            "variables": self._generate_variables(intent),
            "cache": self._generate_cache(intent),
            "stages": self._generate_stages(intent),
            "before_script": self._generate_before_script(intent),
        }

        # Add jobs
        jobs = {}
        if intent.build.enabled:
            jobs.update(self._generate_build_jobs(intent, project_name))

        if intent.test.enabled:
            jobs.update(self._generate_test_jobs(intent, project_name))

        if intent.deploy.enabled:
            jobs.update(self._generate_deploy_jobs(intent, project_name))

        if intent.notification.enabled:
            jobs.update(self._generate_notification_jobs(intent))

        config.update(jobs)

        # Convert to YAML
        return self._to_yaml(config)

    def _get_base_image(self, intent: ExtractedIntent) -> str:
        """Get base Docker image"""
        if intent.environment.docker_enabled and intent.environment.docker_image:
            return intent.environment.docker_image

        # Determine image based on build system
        if intent.build.build_system == BuildSystem.QMAKE:
            return "qt:5.15"

        # Default: modern C++ build environment
        return "ubuntu:22.04"

    def _generate_variables(self, intent: ExtractedIntent) -> Dict[str, str]:
        """Generate global variables"""
        variables = {
            "GIT_SUBMODULE_STRATEGY": "recursive",
            "GIT_DEPTH": "3",
            "CCACHE_DIR": "${CI_PROJECT_DIR}/.ccache",
        }

        # Build type
        if intent.build.build_type:
            variables["BUILD_TYPE"] = intent.build.build_type

        # Parallel jobs
        if intent.build.parallel_jobs > 1:
            variables["PARALLEL_JOBS"] = str(intent.build.parallel_jobs)

        # Environment variables from intent
        if intent.environment.variables:
            variables.update(intent.environment.variables)

        return variables

    def _generate_cache(self, intent: ExtractedIntent) -> Dict[str, Any]:
        """Generate cache configuration"""
        if not intent.cache.enabled:
            return {}

        cache_config = {
            "key": {
                "files": [],  # Will be populated based on build system
            },
            "paths": intent.cache.cache_paths,
        }

        # Add cache key files based on build system
        if intent.build.build_system == BuildSystem.CMAKE:
            cache_config["key"]["files"] = ["CMakeLists.txt", "**/CMakeLists.txt"]
        elif intent.build.build_system == BuildSystem.QMAKE:
            cache_config["key"]["files"] = ["*.pro", "**/*.pro"]
        elif intent.build.build_system in [BuildSystem.MAKE, BuildSystem.NINJA]:
            cache_config["key"]["files"] = ["Makefile", "build.ninja"]

        return cache_config

    def _generate_stages(self, intent: ExtractedIntent) -> List[str]:
        """Generate pipeline stages"""
        stages = []

        if intent.build.enabled:
            stages.append("build")

        if intent.test.enabled:
            stages.append("test")

        if intent.deploy.enabled:
            stages.append("deploy")

        return stages

    def _generate_before_script(self, intent: ExtractedIntent) -> List[str]:
        """Generate before_script commands"""
        script = []

        # Update package list and install dependencies
        if "ubuntu" in self._get_base_image(intent) or "debian" in self._get_base_image(intent):
            script.extend([
                "apt-get update -qq",
                "apt-get install -y -qq build-essential cmake ninja-build ccache",
            ])

            # Add Qt packages for QMake
            if intent.build.build_system == BuildSystem.QMAKE:
                script.append("apt-get install -y -qq qt5-qmake qtbase5-dev qtchooser")

        # Setup ccache
        if intent.build.enable_ccache:
            script.extend([
                "ccache -M 2G",
                "ccache -s",
            ])

        return script

    def _generate_build_jobs(self, intent: ExtractedIntent, project_name: str) -> Dict[str, Any]:
        """Generate build jobs"""
        jobs = {}

        # Main build job
        build_job = {
            "stage": "build",
            "script": self._generate_build_script(intent),
            "artifacts": {
                "paths": self._get_build_artifacts(intent),
                "expire_in": "1 week",
            },
            "cache": {
                "key": f"{self.cache_prefix}-build",
                "paths": [".ccache", "build"],
            },
        }

        # Add rules
        build_job["rules"] = self._generate_build_rules(intent)

        jobs[f"{project_name}:build"] = build_job

        return jobs

    def _generate_build_script(self, intent: ExtractedIntent) -> List[str]:
        """Generate build script commands"""
        script = []

        if intent.build.build_system == BuildSystem.CMAKE:
            script.extend([
                f"cmake -B build -DCMAKE_BUILD_TYPE={intent.build.build_type}",
                "cmake --build build --parallel ${PARALLEL_JOBS:-4}",
            ])

        elif intent.build.build_system == BuildSystem.QMAKE:
            script.extend([
                f"qmake CONFIG+={intent.build.build_type}",
                "make -j${PARALLEL_JOBS:-4}",
            ])

        elif intent.build.build_system == BuildSystem.MAKE:
            script.extend([
                "./configure --prefix=/usr/local",
                "make -j${PARALLEL_JOBS:-4}",
            ])

        elif intent.build.build_system == BuildSystem.NINJA:
            script.extend([
                "meson setup build",
                "ninja -C build -j${PARALLEL_JOBS:-4}",
            ])

        else:  # AUTO or unknown
            # Try CMake first
            script.extend([
                "if [ -f CMakeLists.txt ]; then",
                f"  cmake -B build -DCMAKE_BUILD_TYPE={intent.build.build_type}",
                "  cmake --build build --parallel ${PARALLEL_JOBS:-4}",
                "elif [ -f Makefile ]; then",
                "  make -j${PARALLEL_JOBS:-4}",
                "elif [ -f build.ninja ]; then",
                "  ninja -j${PARALLEL_JOBS:-4}",
                "else",
                "  echo 'Error: No supported build system found'",
                "  exit 1",
                "fi",
            ])

        return script

    def _get_build_artifacts(self, intent: ExtractedIntent) -> List[str]:
        """Get build artifact paths"""
        artifacts = ["build/"]

        if intent.build.build_system == BuildSystem.QMAKE:
            artifacts.extend(["*.a", "*.so", "*.dylib", "*.dll"])

        return artifacts

    def _generate_build_rules(self, intent: ExtractedIntent) -> List[Dict[str, Any]]:
        """Generate build job rules"""
        rules = [
            {
                "if": "$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH",
            },
            {
                "if": "$CI_PIPELINE_SOURCE == 'merge_request_event'",
            },
        ]
        return rules

    def _generate_test_jobs(self, intent: ExtractedIntent, project_name: str) -> Dict[str, Any]:
        """Generate test jobs"""
        jobs = {}

        # Main test job
        test_job = {
            "stage": "test",
            "dependencies": [f"{project_name}:build"] if intent.build.enabled else [],
            "script": self._generate_test_script(intent),
            "coverage": self._generate_coverage_config(intent),
            "artifacts": {
                "reports": {
                    "junit": "test-results/*.xml",
                },
                "paths": ["test-results/", "coverage/"],
                "expire_in": "1 week",
            },
        }

        # Add test timeout
        if intent.test.test_timeout:
            test_job["timeout"] = f"{intent.test.test_timeout}s"

        jobs[f"{project_name}:test"] = test_job

        return jobs

    def _generate_test_script(self, intent: ExtractedIntent) -> List[str]:
        """Generate test script commands"""
        script = []

        # Find tests
        if intent.test.test_discovery:
            script.append("find . -name '*test*' -type f -executable")

        # Run tests based on framework
        if intent.test.framework == TestFramework.QT_TEST:
            script.extend([
                "for test in $(find . -name 'tst_*' -type f -executable); do",
                "  echo \"Running $test\"",
                f"  $test -txt test-results/$(basename $test).txt || true",
                "done",
            ])

        elif intent.test.framework == TestFramework.GTEST:
            script.extend([
                "for test in $(find . -name '*_test' -type f -executable); do",
                "  echo \"Running $test\"",
                f"  $test --gtest_output=xml:test-results/$(basename $test).xml || true",
                "done",
            ])

        else:  # AUTO or unknown
            # Try common patterns
            script.extend([
                "if command -v ctest &> /dev/null; then",
                "  cd build",
                "  ctest --output-on-failure -j${PARALLEL_JOBS:-4} || true",
                "  cd ..",
                "fi",
            ])

        # Run coverage if enabled
        if intent.test.run_coverage:
            script.extend([
                "",
                "# Generate coverage report",
                "lcov --capture --directory . --output-file coverage.info",
                "lcov --remove coverage.info '/usr/*' --output-file coverage.info",
                "lcov --list coverage.info",
                "genhtml coverage.info --output-directory coverage",
            ])

        return script

    def _generate_coverage_config(self, intent: ExtractedIntent) -> Optional[str]:
        """Generate coverage configuration"""
        if intent.test.run_coverage:
            return "/^Total.*?(\\d+\\.\\d+%)$/"
        return None

    def _generate_deploy_jobs(self, intent: ExtractedIntent, project_name: str) -> Dict[str, Any]:
        """Generate deploy jobs"""
        jobs = {}

        for env in intent.deploy.environments:
            job_name = f"{project_name}:deploy:{env}"

            deploy_job = {
                "stage": "deploy",
                "dependencies": [f"{project_name}:build"] if intent.build.enabled else [],
                "script": self._generate_deploy_script(intent, env),
                "environment": {
                    "name": env,
                    "url": self._get_environment_url(env),
                },
                "rules": self._generate_deploy_rules(intent, env),
            }

            jobs[job_name] = deploy_job

        return jobs

    def _generate_deploy_script(self, intent: ExtractedIntent, environment: str) -> List[str]:
        """Generate deploy script for environment"""
        script = [
            f"echo 'Deploying to {environment}'",
        ]

        if intent.deploy.create_artifacts:
            script.extend([
                "# Package artifacts",
                "tar czf artifacts.tar.gz build/",
            ])

        # Add deployment commands based on type
        if intent.deploy.deployment_type == "auto":
            script.append("# Auto-deploy commands here")

        return script

    def _generate_deploy_rules(self, intent: ExtractedIntent, environment: str) -> List[Dict[str, Any]]:
        """Generate deploy job rules"""
        rules = []

        if environment == "production":
            rules.append({
                "if": "$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH && $CI_COMMIT_TAG",
            })
        elif environment == "staging":
            rules.append({
                "if": "$CI_COMMIT_BRANCH == 'staging' || $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH",
            })
        else:
            rules.append({
                "if": f"$CI_COMMIT_BRANCH == '{environment}'",
            })

        # Add manual rule if deployment_type is manual
        if intent.deploy.deployment_type == "manual":
            rules[0]["when"] = "manual"

        return rules

    def _get_environment_url(self, environment: str) -> str:
        """Get environment URL"""
        url_templates = {
            "dev": "https://dev.example.com",
            "test": "https://test.example.com",
            "staging": "https://staging.example.com",
            "production": "https://example.com",
        }
        return url_templates.get(environment, f"https://{environment}.example.com")

    def _generate_notification_jobs(self, intent: ExtractedIntent) -> Dict[str, Any]:
        """Generate notification jobs"""
        jobs = {}

        notify_job = {
            "stage": ".post",  # Run after all other stages
            "script": self._generate_notification_script(intent),
            "when": "always",
            "allow_failure": True,
        }

        jobs["notify"] = notify_job

        return jobs

    def _generate_notification_script(self, intent: ExtractedIntent) -> List[str]:
        """Generate notification script"""
        script = [
            "echo 'Sending notifications...'",
        ]

        # Add notification commands based on channels
        for channel in intent.notification.channels:
            if channel == "email":
                script.append("# Send email notification")
                # script.append("mail -s 'Pipeline $CI_PIPELINE_STATUS' user@example.com")

            elif channel == "slack":
                script.append("# Send Slack notification")
                # script.append("curl -X POST $SLACK_WEBHOOK_URL ...")

            elif channel == "webhook":
                script.append("# Send webhook notification")
                # script.append("curl -X POST $WEBHOOK_URL ...")

        return script

    def _to_yaml(self, config: Dict[str, Any]) -> str:
        """Convert configuration to YAML string"""
        return yaml.dump(config, default_flow_style=False, sort_keys=False, allow_unicode=True)


class CIConfigurationValidator:
    """Validate generated CI configuration"""

    def validate(self, yaml_content: str) -> tuple[bool, List[str]]:
        """
        Validate GitLab CI configuration

        Args:
            yaml_content: YAML configuration string

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        try:
            config = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            return False, [f"YAML syntax error: {str(e)}"]

        # Check for required fields
        if not isinstance(config, dict):
            return False, ["Configuration must be a dictionary"]

        # Validate stages
        if "stages" in config:
            if not isinstance(config["stages"], list):
                errors.append("stages must be a list")

        # Validate jobs
        for job_name, job_config in config.items():
            if job_name in ["image", "variables", "cache", "stages", "before_script", "after_script"]:
                continue  # Skip global configuration

            if not isinstance(job_config, dict):
                errors.append(f"Job '{job_name}' must be a dictionary")
                continue

            # Check for required job fields
            if "stage" not in job_config and job_config.get("stage", "") != ".post":
                errors.append(f"Job '{job_name}' is missing 'stage' field")

            if "script" not in job_config:
                errors.append(f"Job '{job_name}' is missing 'script' field")

        return len(errors) == 0, errors
