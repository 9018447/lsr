<p align="center">
    <a href="https://aider.chat/"><img src="https://aider.chat/assets/logo.svg" alt="Aider Logo" width="300"></a>
</p>

<h1 align="center">
纯AI结对编程工具 (Aider二次开发分支) - 测试编辑功能
</h1>

<p align="center">
区别于自动生成代码的vibe coding类工具，本工具以开发者为核心，AI全程作为结对伙伴提供辅助能力，所有变更均由开发者主导和确认，绝不脱离用户意图自动修改代码。
</p>

<p align="center">
  <img
    src="https://aider.chat/assets/screencast.svg"
    alt="aider screencast"
  >
</p>

## ✨ 核心特性

### 🆕 Hashline 代码行级哈希校验
基于每一行代码的内容和位置生成唯一哈希标识，实现：
- 代码变更的精准定位，避免AI误修改无关代码
- 跨版本代码行匹配，上下文引用永不失效
- 增量变更的完整性校验，确保AI输出的变更完全符合预期

### 🆕 Code-Review-Graph 代码关系全链路分析
内置代码关系图谱能力，可快速查询：
- 函数/类的调用关系、依赖链路、影响范围
- 代码变更的风险评估，自动识别高风险修改点
- 项目结构可视化，快速理解陌生代码库的架构逻辑

### 🆕 多角色专业Agent体系（规划中，暂未实现）
后续版本将内置四类专业编程辅助Agent，覆盖全开发流程：
- 代码评审Agent：基于行业规范和项目最佳实践给出评审意见
- 重构辅助Agent：提供安全重构方案，自动识别重构影响范围
- 调试排障Agent：结合报错信息和代码链路定位根因，给出修复方案
- 架构设计Agent：基于项目现状给出合理的架构演进建议
---

### 原生Aider优秀特性保留
- 支持所有主流云LLM和本地大模型
- 代码库自动映射，大项目上下文理解能力
- 支持100+种编程语言
- 原生Git集成，自动生成规范提交
- 支持IDE内使用、图片/网页上下文、语音输入等能力
- 自动lint和测试，发现问题自动修复

## 🚀 快速开始

### 安装
```bash
# 安装本二次开发版本
pip install git+https://github.com/your-repo/aider.git@prompt-engineering

# 进入你的项目目录
cd /path/to/your/project

# 启动工具（以DeepSeek为例，其他模型参数和原版Aider一致）
aider --model deepseek --api-key deepseek=<your-key>
```

### 基础使用示例
1. **代码关系查询**
```
> /query callers get_user_info
# 自动查询所有调用get_user_info函数的位置和链路
```


3. **Hashline精准修改**
```
> 修改a1b2c3行的参数校验逻辑，增加手机号格式校验
# 基于哈希行标识精准修改指定位置代码，不会误改其他内容
```

## 🆚 与原版Aider的差异
| 功能 | 原版Aider | 本二次开发版本 |
|------|-----------|----------------|
| 定位 | 支持自动编码的AI辅助工具 | 纯结对编程工具，所有变更由开发者主导 |
| 代码变更校验 | 无行级校验，可能出现误改 | 基于Hashline的行级校验，变更100%精准 |
| 代码分析能力 | 仅基础RepoMap | 内置全链路Code-Review-Graph，支持调用关系/影响范围/风险评估 |
| Agent体系 | 通用单一Agent | 多角色专业Agent，覆盖评审/重构/调试/架构全场景 |
| 变更管控 | 仅支持提交前确认 | 支持变更粒度校验、影响范围预评估 |

## 📚 文档
- [Agent体系使用指南](./docs/agents.md)（规划中，暂未实现）
- [Hashline功能详解](./docs/hashline.md)
- [Code-Review-Graph查询语法](./docs/crg.md)
- [原版Aider官方文档](https://aider.chat/docs/)

## 🤝 社区
- 问题反馈：提交Issue到本仓库
- 功能讨论：加入开发者交流群
- 贡献代码：欢迎提交PR完善功能

## 致谢
本项目基于[Aider](https://github.com/Aider-AI/aider)二次开发，感谢原项目的优秀基础。
