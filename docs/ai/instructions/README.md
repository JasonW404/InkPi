# AI Development Instructions

本目录用于固化项目开发规范，所有后续功能开发均需遵守。

## Documents

- [Architecture Rules](architecture-rules.md)
- [Coding Standards](coding-standards.md)
- [Service Contracts](service-contracts.md)
- [Refresh Policy Rules](refresh-policy-rules.md)
- [Quality Gates](quality-gates.md)

## Priority

规范优先级从高到低：

1. 本目录规则
2. `docs/architecture-overview.md`
3. 现有代码风格与模块边界

若发生冲突，必须先更新文档并说明理由，再实施代码变更。

## Environment Baseline

- 本项目 Python 虚拟环境必须通过 `uv venv` 创建。