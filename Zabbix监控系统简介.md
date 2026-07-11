---
tags:
  - zabbix
  - monitoring
  - it-infrastructure
  - devops
  - prometheus
aliases:
  - Zabbix 监控
created: 2026-06-20
---

# Zabbix 监控系统简介

---

## 一、Zabbix 是什么？

> Zabbix 是一款基于 Web 界面的**企业级开源分布式监控系统**（AGPLv3 开源免费），用于监控服务器、虚拟机、网络设备、数据库、Web 应用、云平台等的运行状态和性能指标，并提-供告警与可视化。

---

## 二、核心架构

| 组件 | 作用 |
|:-----|:-----|
| **Zabbix Server** | 核心 —— 接收数据、计算触发器、发告警、存配置 |
| **Database** | 存配置和历史数据（MySQL/PostgreSQL/Oracle 等） |
| **Web 前端** | PHP 写的 Web UI，查看仪表盘、配置监控项 |
| **Zabbix Agent** | 装在被监控主机上采集 CPU/内存/磁盘等（有 C 版和 Go 版 Agent 2） |
| **Zabbix Proxy** | 可选，分布式采集并转发数据，减轻 Server 压力 |

---

## 三、数据采集方式

- Agent 主动/被动模式（Push/Pull）
- 无 Agent 监控：SNMP（网络设备）、IPMI（硬件）、JMX（Java 应用）、ICMP Ping、TCP 端口、SSH/Telnet、HTTP 检查
- 自定义脚本 / UserParameter

---

## 四、主要能力

| 能力 | 说明 |
|:-----|:-----|
| 📊 **监控项 + 触发器** | 灵活定义阈值，超阈值自动转 Problem |
| 🔔 **告警** | 邮件/短信/微信/Webhook，支持告警升级和远程命令自动修复 |
| 📈 **可视化** | 实时图表、自定义图形、网络拓扑图、仪表盘（Dashboard）、报表 |
| 🤖 **自动发现** | 网络发现、Agent 自动注册、低级别发现（自动发现新磁盘/网卡等） |
| 📦 **模板** | 开箱即用的大量官方模板，快速部署 |
| 🔌 **Zabbix API** | 支持批量操作和第三方系统集成 |

---

## 五、典型适用场景

- ✅ 传统 IDC / 机房：物理服务器、交换机路由器监控
- ✅ 企业私有云：VMware/KVM 虚机 + 数据库（MySQL/Oracle/Redis）
- ✅ Web 服务可用性检测（HTTP 状态码、响应时间）
- ⚠️ 不太适合：Kubernetes 等高度动态的云原生环境（通常用 Prometheus + Grafana）

---

## 六、与 Prometheus 简要对比

| 维度 | Zabbix | Prometheus |
|:-----|:--------|:-----------|
| 定位 | 传统 IT 基础设施监控 | 云原生/微服务监控 |
| 存储 | RDBMS（MySQL/PG） | 时序数据库（TSDB） |
| 采集 | Agent + SNMP + Pull/Push | 主要 Pull + Exporter |
| 配置 | Web 界面 + 模板 | YAML 文件 + Service Discovery |
| 强项 | 网络设备/服务器/带 UI 开箱即用 | K8s/容器/动态服务发现 |
