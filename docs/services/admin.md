# inkpi-admin Service

`inkpi-admin` 是 InkPi 的本地 Web 管理门户，面向物理上靠近设备的使用者，
提供状态查看、Dashboard 控制和网络配置入口。

## Service Role

| 职责 | 说明 |
|------|------|
| Web Portal | 提供 no-build HTML 管理界面 |
| Status API | 聚合 core / display / system / network 状态 |
| Dashboard Control | 页面启用/禁用，preview 图片 |
| Network Operations | 允许列表内的网络操作队列（当前为 dry-run） |
| Event Log | 有界、脱敏的管理事件流 |

!!! warning "Not a Display Owner"
    `inkpi-admin` 不渲染 dashboard 帧，不拥有 SPI/GPIO。
    通过 `InkPiClient` 与 `inkpi-core` 通信。

## Access Methods

| 方式 | 说明 |
|------|------|
| LAN | 以太网或 Wi-Fi 局域网直接访问 |
| Hotspot | 设备加入 Pi 热点后访问 |
| Hidden Hotspot | Pi 有互联网时，隐藏热点用于维护 |

默认监听 `127.0.0.1:8080`，可通过启动参数修改。

## Authentication

所有 POST 请求需要 token 验证，提供方式：`X-InkPi-Admin-Token` 或 `Authorization: Bearer` header。
Token 通过 `INKPI_ADMIN_TOKEN` 环境变量配置。
CORS 保护验证 `Origin` 与 `Host` 匹配，不匹配返回 403。

| 场景 | Status |
|------|--------|
| Token 未配置 | 503 |
| Token 无效 | 401 |
| 跨域请求 | 403 |

## API Endpoints

### Read-Only (GET)

| Endpoint | 说明 |
|----------|------|
| `/api/status` | 聚合状态 + auth 配置 |
| `/api/network` | 网络 facts + policy 决策 |
| `/api/dashboard` | Dashboard 状态 + 页面列表 |
| `/api/dashboard/preview/{page_id}.png` | 页面 preview 图片 |
| `/api/display` | Display 服务状态 |
| `/api/system` | 系统 facts |
| `/api/events` | 管理事件流 |

HTML 路由：`/`、`/network`、`/dashboard`、`/system`、`/logs`、`/settings`。

### Mutation (POST, requires token)

| Endpoint | Operation |
|----------|-----------|
| `/api/network/wifi/scan` | `wifi_scan` |
| `/api/network/wifi/connect` | `wifi_connect` |
| `/api/network/wifi/forget` | `wifi_forget` |
| `/api/network/hotspot/enable` | `hotspot_enable` |
| `/api/network/hotspot/disable` | `hotspot_disable` |
| `/api/network/hotspot/rotate-password` | `hotspot_rotate_password` |
| `/api/network/policy/reconcile` | `policy_reconcile` |
| `/api/dashboard/pages/{id}/enable` | 启用页面 |
| `/api/dashboard/pages/{id}/disable` | 禁用页面 |

禁用最后一个 enabled 页面的请求会被 core 拒绝。

## Run Locally

```bash
uv run inkpi-admin --host 127.0.0.1 --port 8080 \
  --core-socket /tmp/inkpi-core.sock --admin-token dev-local-token
```

```bash
curl -X POST -H 'X-InkPi-Admin-Token: dev-local-token' \
  http://127.0.0.1:8080/api/dashboard/pages/codex_usage/disable
```

## Future: NetworkManager Integration

当 privileged helper 实现后，`InMemoryNetworkHelper` 会被替换为真实 IPC 客户端。
Wi-Fi 密码只通过 helper 的 transient secret channel 传递。
详见 [admin-portal-design.md](admin-portal-design.md)。
