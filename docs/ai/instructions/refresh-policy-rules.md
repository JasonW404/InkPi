# Refresh Policy Rules

## Baseline Policy

- 局刷频率：`partial_refresh_interval_seconds`，默认 60。
- 全刷频率：`full_refresh_interval_seconds`，默认 3600。
- 局刷计数阈值：`max_partial_refreshes_before_full`，达到后强制全刷。

## Decision Order

每次刷新决策按如下顺序：

1. 若距离上次全刷达到全刷间隔，执行全刷。
2. 否则若局刷计数达到阈值，执行全刷。
3. 否则执行局刷。

## Safety Rules

- 全刷后必须重置局刷计数。
- 同一时刻仅允许一个刷新任务执行。
- 刷新失败需记录并进入下一周期重试，避免卡死。