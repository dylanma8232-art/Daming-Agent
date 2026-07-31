---
name: docx-exporter
description: 专家级 Word 报告排版与格式导出 SOP 规范流程
---

# Word 报告排版专家 SOP 流程指南

当你需要生成结构严谨、美观规范的 Word (.docx) 格式文档时，请遵循以下规范：

## 1. 结构化设计要求
- **文档大标题 (Title)**：必须简明扼要，居中居顶。
- **章节划分 (Heading Levels)**：
  - Level 1：一级大章节标题（如 `第一章：项目概要`）。
  - Level 2：二级小节标题（如 `1.1 核心收益`）。
- **正文段落 (Paragraph)**：逻辑分段清晰，避免大段堆砌。
- **项目列表 (Bullets)**：使用列表展示要点与优势。
- **表格 (Tables)**：包含明确的表头与对齐规则。

## 2. 工具调用规范
使用 `create_word_document` 工具，构建对应的 `sections` 数据结构：
```json
{
  "relative_path": "report.docx",
  "title": "年度业务分析报告",
  "sections": [
    {"type": "heading", "level": 1, "text": "一、 总结概述"},
    {"type": "paragraph", "text": "本报告汇总了本年度核心业务数据。"},
    {"type": "bullet", "items": ["增长率提升 25%", "成本降低 15%"]},
    {"type": "table", "headers": ["指标", "数值"], "rows": [["营收", "1000万"], ["净利", "200万"]]}
  ]
}
```
