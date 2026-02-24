# Coding Standards

## General

- Python 版本固定为 3.12。
- 使用 `uv` 执行虚拟环境创建、安装、运行、测试。
- 虚拟环境必须使用 `uv venv` 创建。
- 禁止使用 `python -m venv` 或 `virtualenv`。
- 新代码采用类型注解和数据类优先。

## Documentation

- 每个 Python 文件头部必须包含模块级 docstring，简述文件用途。
- 按照 Google Style 编写精简 docstring，包含：
  - 模块/类/函数用途描述
  - 复杂函数的 Args/Returns/Raises（简要）
- 避免冗余注释，仅对关键逻辑或非显而易见行为加注释。

## Naming

- 配置类以 `*Config` 结尾。
- 服务实现以 `*Service` 或 `*Provider` 结尾。
- 渲染组件以 `*Panel` 或 `*Renderer` 结尾。

## Error Handling

- 外部请求必须设置超时。
- provider 失败时返回降级数据，不直接使主循环崩溃。
- 所有异常需包含上下文信息（provider 名称、操作、关键参数）。

## File Organization

- 每个模块保持单一职责。
- 避免在 `main.py` 中堆积业务逻辑。
- 复杂逻辑必须拆分到 `src/` 子模块。