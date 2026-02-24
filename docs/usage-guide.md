# 使用指南 - eInk Dashboard

## 快速开始

### 1. 环境配置

复制配置示例文件并编辑：

```bash
cp .env.example .env
```

编辑 `.env` 文件，设置你的配置：

```bash
# 必需配置
EINK_GITHUB_USERNAME=你的GitHub用户名
EINK_GITHUB_ORG=你的GitHub组织名
EINK_WEATHER_LOCATION=上海

# 可选配置
EINK_TIMEZONE=Asia/Shanghai
EINK_GITHUB_API_KEY=你的GitHub Token（可选，用于私有仓库数据）
```

### 2. 生成预览

```bash
# 使用环境变量
export $(cat .env | xargs)
uv run python preview.py

# 或者直接指定环境变量
EINK_WEATHER_LOCATION="上海" EINK_TIMEZONE="Asia/Shanghai" uv run python preview.py
```

预览图将保存到 `preview.png`。

### 3. 运行Dashboard

```bash
# 加载环境变量
export $(cat .env | xargs)

# 启动dashboard应用
uv run python main.py
```

## 配置说明

### GitHub配置

- `EINK_GITHUB_USERNAME`: 你的GitHub用户名（必需）
- `EINK_GITHUB_ORG`: 你的GitHub组织名（必需）
- `EINK_GITHUB_API_KEY`: GitHub Personal Access Token（可选）
  - 用于访问私有仓库数据
  - 创建Token: https://github.com/settings/tokens
  - 所需权限: `repo` (读取仓库)

### 天气配置

- `EINK_WEATHER_LOCATION`: 位置（必需）
  - 支持中文地名: `"上海"`, `"北京"`, `"广州"`
  - 支持英文地名: `"Shanghai"`, `"Paris"`, `"New York"`
  - 支持坐标: `"31.2304,121.4737"` (纬度,经度)
  
- `EINK_TIMEZONE`: 时区（默认: UTC）
  - 示例: `Asia/Shanghai`, `America/New_York`, `Europe/Paris`
  - 完整列表: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

### 知识卡片配置

- `EINK_KNOWLEDGE_LOCAL_FILE`: 本地JSON文件路径（默认: data/cards.json）
- `EINK_KNOWLEDGE_REMOTE_ENABLED`: 启用远程卡片（0或1）
- `EINK_KNOWLEDGE_REMOTE_URL`: 远程JSON URL

知识卡片JSON格式：

```json
[
  {
    "title": "卡片标题",
    "body": "卡片内容...",
    "source": "来源"
  }
]
```

### 刷新策略配置

- `EINK_PARTIAL_REFRESH_INTERVAL_SECONDS`: 局部刷新间隔（秒，默认60）
- `EINK_FULL_REFRESH_INTERVAL_SECONDS`: 完全刷新间隔（秒，默认3600）
- `EINK_MAX_PARTIAL_REFRESHES_BEFORE_FULL`: 强制完全刷新前的最大局部刷新次数（默认30）

## 数据源状态

当前所有数据源均使用真实数据：

- ✓ **DateTime**: 系统时间（支持时区）
- ✓ **Weather**: Open-Meteo实时天气（支持地理编码）
- ✓ **System Load**: 实时系统负载
- ✓ **GitHub**: 用户贡献 + 组织统计
- ✓ **Knowledge Cards**: 本地/远程JSON文件

## 故障排除

### GitHub数据为空

1. 确认用户名和组织名正确
2. 检查网络连接
3. 如需私有仓库数据，设置 `EINK_GITHUB_API_KEY`

### 天气数据无法获取

1. 检查位置拼写是否正确
2. 尝试使用更简单的地名（如"上海"而不是"上海市青浦区"）
3. 可以使用经纬度坐标作为备用方案

### 时区显示错误

1. 确认时区名称正确（参考tz database）
2. 检查系统是否安装了时区数据包
3. 默认使用UTC时区

## 下一步

- [ ] 实现EPD显示适配器（连接到实际墨水屏）
- [ ] 添加脏区域追踪优化
- [ ] 完善错误重试和超时策略
- [ ] 添加单元测试
