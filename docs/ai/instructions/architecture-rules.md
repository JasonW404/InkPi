# Architecture Rules

## Layer Boundaries

- `src/config.py` 仅负责配置与装配，不执行业务采集逻辑。
- `src/services/` 仅负责外部数据采集与标准化，不直接操作显示驱动。
- `src/ui/` 仅负责布局和渲染，不直接访问网络。
- `src/display/`（规划中）仅负责硬件显示适配，不拼装业务数据。
- `src/app.py` 负责调度与依赖注入，不编写 provider 细节。

## Dependency Direction

- 允许：`app -> services/ui/display/config/domain`
- 禁止：`services -> ui/display`，`ui -> services`。

## Extensibility Rules

- 新增数据源必须通过协议接口接入，不允许直接耦合到主循环。
- 新增面板必须先定义领域模型，再定义渲染组件。
- 任何跨层变更都要同步更新文档。