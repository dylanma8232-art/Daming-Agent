---
name: code-auditor
description: 代码质量规范审计与安全漏洞检测 SOP
---

# 代码质量与安全审计 SOP 指南

当你受命对指定代码文件或工作区项目进行评审与审计时，请严格执行以下三步法 SOP：

## 1. 代码读取与精准定位
- 先使用 `list_files` 查看项目文件分布；
- 对于特定代码文件，使用 `read_file_lines` 读取核心行号段，严禁未经阅读盲目给意见。

## 2. 核心审计维度
- **安全性 (Security)**：检查 SQL 注入、硬编码敏感秘钥、Command Injection (如未加干预的 shell 执行)、路径穿越问题。
- **性能与鲁棒性 (Performance)**：检查资源未关闭、无限循环、未捕获的异常崩溃点。
- **代码规范 (Style)**：检查函数命名规范、类型注解补全及冗余废代码。

## 3. 修复与重构输出
- 若需修改代码，优先使用 `replace_file_content` 工具进行精准局部替换。
- 给出清晰的 Audit Summary 报告。
