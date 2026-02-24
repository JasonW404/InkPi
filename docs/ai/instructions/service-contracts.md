# Service Contracts

## Contract Principles

- 所有服务返回结构化领域对象，不返回未清洗原始 API 数据。
- 返回对象必须包含最小可渲染字段。
- 不得在服务层返回 UI 文案拼接结果。

## GitHub Service

- 输入：用户名、组织名、月份范围、API Key（需包含私仓读权限才能统计私仓数据）。
- 输出:
  - 当月日历矩阵
  - 组织 repo 数
  - 当月 commit 总数
  - 当月代码增减总量

## Weather Service

- 输入：地点、时区、API 配置。
- 输出：当前天气摘要、温度区间、更新时间。

## System Service

- 输入：系统负载采样。
- 输出：0-5 档负载等级（每 20% 一档）。

## Knowledge Card Service

- 输入：本地源配置 + 可选远程源配置。
- 输出：单条当前卡片（标题、正文、来源、更新时间）。
- 策略：本地优先；远程成功时覆盖。