#!/usr/bin/env python3
"""
AI-CICD LLM 集成测试脚本

测试智谱AI、Claude等LLM的集成和AI功能
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.core.llm.factory import get_llm_client, get_available_providers
from src.utils.config import settings
from src.utils.logger import setup_logging, get_logger


# 设置日志
setup_logging(level="INFO", log_format="console")
logger = get_logger(__name__)


async def test_llm_status():
    """测试1: 检查LLM配置状态"""
    print("\n" + "="*60)
    print("测试1: 检查LLM配置状态")
    print("="*60)

    available = get_available_providers()
    print(f"\n✅ 可用的LLM提供商: {', '.join(available) if available else '无'}")
    print(f"📌 默认提供商: {settings.default_llm_provider}")

    print("\n配置详情:")
    print(f"  智谱AI: {'✅ 已配置' if settings.zhipu_api_key else '❌ 未配置'}")
    if settings.zhipu_api_key:
        print(f"    模型: {settings.zhipu_model}")
        print(f"    API Key: {settings.zhipu_api_key[:10]}...")

    print(f"  Claude: {'✅ 已配置' if settings.anthropic_api_key else '❌ 未配置'}")
    if settings.anthropic_api_key:
        print(f"    模型: {settings.claude_model}")

    print(f"  OpenAI: {'✅ 已配置' if settings.openai_api_key else '❌ 未配置'}")
    if settings.openai_api_key:
        print(f"    模型: {settings.openai_model}")

    if not available:
        print("\n⚠️  错误: 没有可用的LLM提供商，请在.env文件中配置API密钥")
        return False

    return True


async def test_basic_generation():
    """测试2: 基本文本生成"""
    print("\n" + "="*60)
    print("测试2: 基本文本生成")
    print("="*60)

    try:
        client = get_llm_client()
        if client is None:
            print("❌ 无法获取LLM客户端")
            return False

        print(f"\n🤖 使用模型: {client.model if hasattr(client, 'model') else 'unknown'}")

        prompt = "你好，请用一句话介绍你自己。"
        print(f"📝 提示词: {prompt}")

        print("\n⏳ 正在生成...")
        response = await client.generate(
            prompt=prompt,
            temperature=0.7,
            max_tokens=200,
        )

        print(f"\n✅ 生成成功!")
        print(f"📄 响应: {response}")
        print(f"📊 响应长度: {len(response)} 字符")
        return True

    except Exception as e:
        print(f"\n❌ 生成失败: {e}")
        logger.error("basic_generation_failed", error=str(e))
        return False


async def test_code_review():
    """测试3: AI代码审查"""
    print("\n" + "="*60)
    print("测试3: AI代码审查")
    print("="*60)

    try:
        client = get_llm_client()
        if client is None:
            print("❌ 无法获取LLM客户端")
            return False

        # 测试代码
        code = """
#include <iostream>
using namespace std;

int main() {
    int* ptr = new int(42);
    cout << *ptr << endl;
    // 忘记释放内存!
    return 0;
}
"""

        print(f"\n📝 待审查的代码:{code}")

        system_prompt = """你是一个经验丰富的C++代码审查专家。
请分析代码中的潜在问题，包括：
1. 内存泄漏
2. 安全问题
3. 代码质量
4. 最佳实践

请简要指出问题并提供改进建议。"""

        print("\n⏳ 正在分析代码...")
        response = await client.generate(
            prompt=f"请审查以下C++代码：\n```cpp\n{code}\n```",
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=1000,
        )

        print(f"\n✅ 审查完成!")
        print(f"📄 审查结果:\n{response}")
        return True

    except Exception as e:
        print(f"\n❌ 审查失败: {e}")
        logger.error("code_review_failed", error=str(e))
        return False


async def test_test_selection():
    """测试4: 智能测试选择"""
    print("\n" + "="*60)
    print("测试4: 智能测试选择")
    print("="*60)

    try:
        client = get_llm_client()
        if client is None:
            print("❌ 无法获取LLM客户端")
            return False

        changed_files = [
            "src/services/user_service.cpp",
            "src/models/user.h",
            "tests/unit/user_test.cpp",
        ]

        print(f"\n📝 变更的文件:")
        for f in changed_files:
            print(f"  - {f}")

        system_prompt = """你是一个测试策略专家。
基于代码变更，分析影响域并推荐需要运行的测试。
重点关注：
1. 受影响的功能模块
2. 需要优先执行的测试
3. 可能遗漏的测试场景"""

        print("\n⏳ 正在分析影响域...")
        response = await client.generate(
            prompt=f"以下文件发生了变更，请分析影响域并推荐测试：\n" + "\n".join(f"- {f}" for f in changed_files),
            system_prompt=system_prompt,
            temperature=0.5,
            max_tokens=800,
        )

        print(f"\n✅ 分析完成!")
        print(f"📄 测试选择建议:\n{response}")
        return True

    except Exception as e:
        print(f"\n❌ 分析失败: {e}")
        logger.error("test_selection_failed", error=str(e))
        return False


async def test_ci_generation():
    """测试5: CI/CD配置生成"""
    print("\n" + "="*60)
    print("测试5: CI/CD配置生成")
    print("="*60)

    try:
        client = get_llm_client()
        if client is None:
            print("❌ 无法获取LLM客户端")
            return False

        prompt = """我需要一个C++项目的GitLab CI配置，要求：
1. 使用CMake构建
2. 运行单元测试
3. 代码覆盖率检查
4. 支持 GCC 和 Clang 编译器

请生成 .gitlab-ci.yml 配置文件。"""

        print(f"\n📝 需求: {prompt}")

        print("\n⏳ 正在生成配置...")
        response = await client.generate(
            prompt=prompt,
            temperature=0.3,
            max_tokens=1500,
        )

        print(f"\n✅ 生成完成!")
        print(f"📄 生成的配置:\n{response}")
        return True

    except Exception as e:
        print(f"\n❌ 生成失败: {e}")
        logger.error("ci_generation_failed", error=str(e))
        return False


async def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("🚀 AI-CICD LLM 集成测试")
    print("="*60)

    results = {}

    # 测试1: 检查配置
    if not await test_llm_status():
        print("\n❌ LLM未配置，测试终止")
        return

    # 测试2: 基本生成
    results["basic_generation"] = await test_basic_generation()

    # 测试3: 代码审查
    results["code_review"] = await test_code_review()

    # 测试4: 测试选择
    results["test_selection"] = await test_test_selection()

    # 测试5: CI生成
    results["ci_generation"] = await test_ci_generation()

    # 总结
    print("\n" + "="*60)
    print("📊 测试总结")
    print("="*60)

    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{test_name:20s}: {status}")

    total = len(results)
    passed = sum(results.values())
    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n🎉 所有测试通过！LLM集成工作正常。")
    else:
        print(f"\n⚠️  {total - passed} 个测试失败，请检查配置和网络连接。")


if __name__ == "__main__":
    asyncio.run(main())
