"""
Natural Language Configuration Service

Provides natural language to CI/CD configuration generation.
"""
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path

from .intent import IntentExtractor, ExtractedIntent
from .generator import GitLabCIGenerator, CIConfigurationValidator
from ....core.llm.factory import get_llm_client


class NLConfigService:
    """Natural language configuration service"""

    def __init__(self):
        self.intent_extractor = IntentExtractor()
        self.ci_generator = GitLabCIGenerator()
        self.validator = CIConfigurationValidator()

    async def generate_config(
        self,
        description: str,
        project_name: str = "project",
        use_ai_enhancement: bool = True,
    ) -> Dict[str, Any]:
        """
        Generate CI/CD configuration from natural language description

        Args:
            description: Natural language description of desired CI/CD pipeline
            project_name: Name of the project
            use_ai_enhancement: Whether to use AI for enhanced understanding

        Returns:
            Dictionary containing:
                - success: bool
                - config: str (Generated YAML configuration)
                - intent: ExtractedIntent
                - validation: dict
                - explanation: str (AI-generated explanation if enabled)
        """
        try:
            # Extract intent from natural language
            intent = self.intent_extractor.extract(description)

            # Generate configuration
            config_yaml = self.ci_generator.generate(intent, project_name)

            # Validate configuration
            is_valid, validation_errors = self.validator.validate(config_yaml)

            # AI enhancement (optional)
            explanation = None
            if use_ai_enhancement:
                explanation = await self._generate_explanation(
                    description, intent, config_yaml
                )

            return {
                "success": True,
                "config": config_yaml,
                "intent": intent,
                "validation": {
                    "valid": is_valid,
                    "errors": validation_errors,
                },
                "explanation": explanation,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    async def _generate_explanation(
        self,
        description: str,
        intent: ExtractedIntent,
        config: str,
    ) -> str:
        """
        Generate AI explanation of the configuration

        Args:
            description: Original user description
            intent: Extracted intent
            config: Generated configuration

        Returns:
            Explanation string
        """
        llm_client = get_llm_client()

        prompt = f"""Explain the following GitLab CI/CD configuration in simple terms:

User Request: {description}

Generated Configuration:
```yaml
{config[:2000]}  # Truncate for token efficiency
```

Provide a clear explanation that covers:
1. What stages are included and why
2. What the build process does
3. How tests are executed
4. Any deployment automation
5. Key optimizations (caching, parallelization, etc.)

Keep the explanation concise and user-friendly.
"""

        try:
            response = await llm_client.complete(prompt, max_tokens=1000)
            return response.strip()
        except Exception as e:
            # Fallback to basic explanation
            return self._generate_basic_explanation(intent)

    def _generate_basic_explanation(self, intent: ExtractedIntent) -> str:
        """Generate basic explanation without AI"""
        parts = []

        if intent.build.enabled:
            parts.append(f"**Build Stage**: Compiles your code using {intent.build.build_system.value} in {intent.build.build_type} mode with {intent.build.parallel_jobs} parallel jobs.")

        if intent.cache.enabled:
            parts.append("**Caching**: Uses ccache and build cache to speed up subsequent builds.")

        if intent.test.enabled:
            test_desc = f"**Test Stage**: Runs your tests"
            if intent.test.run_coverage:
                test_desc += " with code coverage reporting"
            if intent.test.parallel_execution:
                test_desc += " in parallel"
            parts.append(test_desc + ".")

        if intent.deploy.enabled:
            parts.append(f"**Deploy Stage**: Deploys to {', '.join(intent.deploy.environments)} environment(s) using {intent.deploy.deployment_type} deployment.")

        if intent.notification.enabled:
            parts.append(f"**Notifications**: Sends notifications on {'success and ' if intent.notification.on_success else ''}{'failure' if intent.notification.on_failure else ''} via {', '.join(intent.notification.channels)}.")

        return "\n\n".join(parts) if parts else "Basic CI/CD pipeline configuration."

    async def optimize_config(
        self,
        current_config: str,
        optimization_goals: list[str],
    ) -> Dict[str, Any]:
        """
        Optimize existing CI/CD configuration

        Args:
            current_config: Current YAML configuration
            optimization_goals: List of goals (e.g., ["speed", "cost", "reliability"])

        Returns:
            Dictionary with optimized config and suggestions
        """
        suggestions = []

        # Analyze current config
        try:
            import yaml
            config_dict = yaml.safe_load(current_config)

            # Check for caching
            if "cache" not in config_dict and "speed" in optimization_goals:
                suggestions.append({
                    "type": "cache",
                    "priority": "high",
                    "message": "Add caching to speed up builds",
                    "suggestion": """cache:
  key: ${CI_COMMIT_REF_SLUG}
  paths:
    - .ccache
    - build/""",
                })

            # Check for parallel jobs
            if "speed" in optimization_goals:
                for job_name, job_config in config_dict.items():
                    if isinstance(job_config, dict) and "script" in job_config:
                        # Check if parallel execution is used
                        script = job_config.get("script", [])
                        if isinstance(script, list) and "parallel" not in " ".join(script):
                            suggestions.append({
                                "type": "parallelization",
                                "priority": "medium",
                                "message": f"Add parallel execution to job '{job_name}'",
                                "job": job_name,
                            })

            # Check for artifacts
            if "cost" in optimization_goals:
                for job_name, job_config in config_dict.items():
                    if isinstance(job_config, dict) and "artifacts" in job_config:
                        artifacts = job_config["artifacts"]
                        if isinstance(artifacts, dict):
                            expire_in = artifacts.get("expire_in")
                            if expire_in and "week" in expire_in:
                                suggestions.append({
                                    "type": "artifacts",
                                    "priority": "low",
                                    "message": f"Reduce artifact expiration time in job '{job_name}' to save storage costs",
                                    "job": job_name,
                                })

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to analyze configuration: {str(e)}",
            }

        # Generate optimized config using AI
        optimized_config = current_config
        if suggestions:
            optimized_config = await self._apply_ai_optimizations(
                current_config, suggestions, optimization_goals
            )

        return {
            "success": True,
            "optimized_config": optimized_config,
            "suggestions": suggestions,
            "optimization_goals": optimization_goals,
        }

    async def _apply_ai_optimizations(
        self,
        config: str,
        suggestions: list[Dict[str, Any]],
        goals: list[str],
    ) -> str:
        """Use AI to apply optimizations"""
        llm_client = get_llm_client()

        # Format suggestions for AI
        suggestions_text = "\n".join([
            f"- {s['message']} (Priority: {s['priority']})"
            for s in suggestions[:5]  # Limit to top 5
        ])

        prompt = f"""Optimize the following GitLab CI/CD configuration with these goals: {', '.join(goals)}.

Suggestions:
{suggestions_text}

Current Configuration:
```yaml
{config[:3000]}
```

Apply the most important optimizations while maintaining functionality. Return only the optimized YAML configuration.
"""

        try:
            response = await llm_client.complete(prompt, max_tokens=2000)
            return response.strip()
        except Exception:
            return config  # Return original if AI fails

    def explain_config(self, yaml_content: str) -> Dict[str, Any]:
        """
        Explain a CI/CD configuration

        Args:
            yaml_content: YAML configuration to explain

        Returns:
            Explanation breakdown
        """
        try:
            import yaml
            config = yaml.safe_load(yaml_content)

            explanation = {
                "stages": config.get("stages", []),
                "jobs": [],
                "services": config.get("services", []),
                "variables": config.get("variables", {}),
                "cache": config.get("cache", None),
            }

            # Analyze jobs
            for job_name, job_config in config.items():
                if job_name in ["stages", "variables", "cache", "services", "before_script", "after_script", "image"]:
                    continue

                if isinstance(job_config, dict):
                    job_info = {
                        "name": job_name,
                        "stage": job_config.get("stage", "unknown"),
                        "description": self._describe_job(job_name, job_config),
                    }
                    explanation["jobs"].append(job_info)

            return {
                "success": True,
                "explanation": explanation,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    def _describe_job(self, job_name: str, job_config: Dict[str, Any]) -> str:
        """Generate a description for a job"""
        stage = job_config.get("stage", "unknown")
        script = job_config.get("script", [])

        if not script:
            return f"Job in {stage} stage"

        # Analyze script
        script_str = " ".join(script) if isinstance(script, list) else str(script)

        if "build" in script_str.lower():
            return f"Builds the project in {stage} stage"
        elif "test" in script_str.lower():
            return f"Runs tests in {stage} stage"
        elif "deploy" in script_str.lower():
            return f"Deploys application in {stage} stage"
        else:
            return f"Job in {stage} stage"

    async def complete_config(
        self,
        partial_config: str,
        user_goal: str,
    ) -> Dict[str, Any]:
        """
        Complete a partial CI/CD configuration based on user goal

        Args:
            partial_config: Partial YAML configuration
            user_goal: Description of what needs to be completed

        Returns:
            Completed configuration
        """
        llm_client = get_llm_client()

        prompt = f"""Complete the following partial GitLab CI/CD configuration based on the user's goal.

User Goal: {user_goal}

Partial Configuration:
```yaml
{partial_config[:2000]}
```

Complete the configuration by adding missing stages, jobs, or configurations needed to achieve the user's goal. Return only the complete, valid YAML configuration.
"""

        try:
            response = await llm_client.complete(prompt, max_tokens=2000)
            completed_config = response.strip()

            # Validate
            is_valid, errors = self.validator.validate(completed_config)

            return {
                "success": is_valid,
                "config": completed_config,
                "validation_errors": errors,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }


# Singleton instance
nl_config_service = NLConfigService()
