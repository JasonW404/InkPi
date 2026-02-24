# UI Rendering Module

本模块实现 800x480 横屏 4 灰度墨水屏渲染。

## Architecture

```
src/ui/
├── __init__.py          # 包导出
├── constants.py         # 屏幕尺寸与灰度常量
├── drawing.py           # 绘图工具函数
├── renderer.py          # 主渲染器（组合所有面板）
├── sidebar_panel.py     # 左侧信息栏（日期/天气/系统）
├── knowledge_card_panel.py  # 知识卡片面板
└── github_panel.py      # GitHub 统计面板
```

## Layout

```
┌─────────────┬────────────────────────────────┐
│             │                                │
│  Sidebar    │     Knowledge Card Panel      │
│  (200px)    │                                │
│             ├────────────────────────────────┤
│  Date/Time  │                                │
│  Weather    │      GitHub Statistics        │
│  System     │      & Contribution Calendar  │
│             │                                │
└─────────────┴────────────────────────────────┘
     800 x 480 (landscape)
```

## Usage

### Generate Preview

```bash
uv run python preview.py
```

这会生成 `preview.png` 用于验证布局和灰度效果。

### In Application

`DashboardRenderer` 已集成到 `src/app.py` 的主循环中。每个刷新周期会：

1. 调用 `DashboardDataService.collect()` 获取数据快照
2. 调用 `DashboardRenderer.render(snapshot)` 生成图像
3. （待实现）将图像发送到 EPD 适配层进行屏幕刷新

## Grayscale Palette

4 灰度级别定义在 `constants.py`：

- `GRAY_WHITE = 255` （白色背景）
- `GRAY_LIGHT = 170` （浅灰）
- `GRAY_MID = 85` （中灰）
- `GRAY_BLACK = 0` （黑色文字）

## Panel Customization

每个面板继承相同模式：

```python
class MyPanel:
    def __init__(self, width: int, height: int) -> None:
        self._width = width
        self._height = height

    def render(self, data: MyData) -> Image.Image:
        image = Image.new("L", (self._width, self._height), GRAY_WHITE)
        # ... drawing logic ...
        return image
```

修改布局时，调整 `renderer.py` 中的尺寸常量和 paste 坐标即可。
