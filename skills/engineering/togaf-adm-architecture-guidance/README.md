> **🤖 AI-Maintained** — This repository is maintained by AI agents. Human commits (perhaps) zero. Liability (certainly) none. Fun (definitely) infinite.

# TOGAF Skill - 企业架构框架

## 概述

TOGAF (The Open Group Architecture Framework) 是业界最广泛使用的企业架构框架。本技能提供 TOGAF 方法论、ADM 流程、架构内容框架和最佳实践指南，帮助架构师高效开展企业架构工作。

## 何时使用

当用户需要：
- 了解或应用 TOGAF 企业架构框架
- 执行 ADM（架构开发方法）流程
- 创建 TOGAF 架构制品和交付物
- 设计架构视图和视角
- 建立架构治理机制
- 制定架构原则和标准

## TOGAF 核心组件

```
┌─────────────────────────────────────────────────────────────────────┐
│                    TOGAF Architecture Framework                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              ADM (Architecture Development Method)           │   │
│  │                                                               │   │
│  │    Preliminary ──► A.Vision ──► B.Business ──► C.IS ──►     │   │
│  │         │                                          │         │   │
│  │         │    Requirements ◄──► D.Technology ◄─────┘         │   │
│  │         │    Management          │                           │   │
│  │         │                        ▼                           │   │
│  │         └────── H.Change ◄── G.Gov ◄── F.Migration ◄──     │   │
│  │                                                     │         │   │
│  │                            E.Opportunities ◄───────┘         │   │
│  │                              & Solutions                      │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────┐   │
│  │   Enterprise   │  │   Architecture │  │   Architecture     │   │
│  │   Continuum    │  │   Repository   │  │   Capability       │   │
│  └────────────────┘  └────────────────┘  └────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## ADM 阶段详解

### Preliminary Phase（预备阶段）

**目的**: 准备组织实施企业架构

**主要活动**:
- 定义架构组织和治理框架
- 确认架构原则
- 选择并定制架构框架
- 实施架构工具

**关键交付物**:
- Architecture Principles（架构原则）
- Organizational Model for EA（EA组织模型）
- Tailored Architecture Framework（定制架构框架）
- Architecture Repository（架构库）初始化

### Phase A: Architecture Vision（架构愿景）

**目的**: 开发架构愿景，获得利益相关者批准

**主要活动**:
- 建立架构项目
- 识别利益相关者和关注点
- 确认业务目标和驱动力
- 定义范围和约束
- 确认架构原则
- 开发架构愿景

**关键交付物**:
- Statement of Architecture Work（架构工作声明）
- Architecture Vision（架构愿景）
- Stakeholder Map Matrix（利益相关者矩阵）
- Communications Plan（沟通计划）

### Phase B: Business Architecture（业务架构）

**目的**: 描述基线和目标业务架构

**主要活动**:
- 选择参考模型、视角和工具
- 开发基线业务架构描述
- 开发目标业务架构描述
- 执行差距分析
- 定义路线图组件

**关键交付物**:
- Business Architecture Document（业务架构文档）
- Business Process Models（业务流程模型）
- Business Capability Map（业务能力地图）
- Organization Map（组织架构图）

### Phase C: Information Systems Architecture（信息系统架构）

**目的**: 描述数据和应用架构

#### C1: Data Architecture（数据架构）

**主要活动**:
- 开发基线数据架构描述
- 开发目标数据架构描述
- 执行差距分析

**关键交付物**:
- Data Architecture Document（数据架构文档）
- Data Entity/Business Function Matrix（数据实体/业务功能矩阵）
- Conceptual Data Model（概念数据模型）
- Logical Data Model（逻辑数据模型）

#### C2: Application Architecture（应用架构）

**主要活动**:
- 开发基线应用架构描述
- 开发目标应用架构描述
- 执行差距分析

**关键交付物**:
- Application Architecture Document（应用架构文档）
- Application Portfolio Catalog（应用组合目录）
- Application Communication Diagram（应用通信图）
- Application/Data Matrix（应用/数据矩阵）

### Phase D: Technology Architecture（技术架构）

**目的**: 描述技术基础设施

**主要活动**:
- 开发基线技术架构描述
- 开发目标技术架构描述
- 执行差距分析

**关键交付物**:
- Technology Architecture Document（技术架构文档）
- Technology Standards Catalog（技术标准目录）
- Technology Portfolio Catalog（技术组合目录）
- Environments and Locations Diagram（环境和位置图）

### Phase E: Opportunities and Solutions（机会与解决方案）

**目的**: 进行实施规划，识别交付载体

**主要活动**:
- 确定关键项目
- 评估依赖关系
- 确认路线图
- 定义架构合同

**关键交付物**:
- Implementation and Migration Strategy（实施和迁移策略）
- Architecture Roadmap（架构路线图）
- Work Packages（工作包）
- Solution Building Blocks (SBBs)

### Phase F: Migration Planning（迁移规划）

**目的**: 制定详细的实施和迁移计划

**主要活动**:
- 协调迁移计划
- 完成架构合同
- 确定业务价值
- 确认架构路线图

**关键交付物**:
- Implementation and Migration Plan（实施和迁移计划）
- Transition Architectures（过渡架构）
- Implementation Governance Model（实施治理模型）

### Phase G: Implementation Governance（实施治理）

**目的**: 确保架构实施符合规范

**主要活动**:
- 确认实施范围
- 识别部署计划
- 执行企业架构合规审查
- 执行实施后评审

**关键交付物**:
- Architecture Contract（架构合同）
- Compliance Assessments（合规评估）
- Architecture-compliant Implemented Systems（符合架构的实施系统）

### Phase H: Architecture Change Management（架构变更管理）

**目的**: 管理架构变更

**主要活动**:
- 建立变更管理流程
- 管理变更请求
- 评估变更影响

**关键交付物**:
- Architecture Updates（架构更新）
- Change Requests（变更请求）
- Assessment Reports（评估报告）

### Requirements Management（需求管理）

**目的**: 贯穿 ADM 全程，管理架构需求

**主要活动**:
- 识别和存储需求
- 确定需求优先级
- 管理需求变更

## 架构内容框架

### Content Metamodel（内容元模型）

```
┌──────────────────────────────────────────────────────────────────────┐
│                      Architecture Content Metamodel                   │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │
│   │  Business   │    │   Data      │    │ Application │             │
│   │  Entities   │    │  Entities   │    │  Entities   │             │
│   ├─────────────┤    ├─────────────┤    ├─────────────┤             │
│   │ • Actor     │    │ • Data      │    │ • App       │             │
│   │ • Role      │    │   Entity    │    │   Component │             │
│   │ • Business  │    │ • Logical   │    │ • App       │             │
│   │   Service   │    │   Data      │    │   Service   │             │
│   │ • Process   │    │   Component │    │ • Interface │             │
│   │ • Function  │    │ • Physical  │    │             │             │
│   │ • Event     │    │   Data      │    │             │             │
│   │ • Product   │    │   Component │    │             │             │
│   │ • Contract  │    │             │    │             │             │
│   └─────────────┘    └─────────────┘    └─────────────┘             │
│                                                                       │
│   ┌─────────────┐    ┌─────────────────────────────────────────┐    │
│   │ Technology  │    │           Cross-Cutting Entities        │    │
│   │  Entities   │    ├─────────────────────────────────────────┤    │
│   ├─────────────┤    │ • Location    • Capability              │    │
│   │ • Platform  │    │ • Assumption  • Constraint              │    │
│   │   Service   │    │ • Requirement • Gap                     │    │
│   │ • Tech      │    │ • Principle   • Work Package            │    │
│   │   Component │    │ • Objective   • Standard                │    │
│   │ • Node      │    │ • Driver      • Goal                    │    │
│   └─────────────┘    └─────────────────────────────────────────┘    │
│                                                                       │
└──────────────────────────────────────────────────────────────────────┘
```

### Building Blocks（构建块）

#### ABB - Architecture Building Block（架构构建块）

定义功能和内容的逻辑组件，与具体实现无关。

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ABB 类型示例                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Business ABBs:                                                      │
│  • Customer Onboarding Capability                                    │
│  • Payment Processing Capability                                     │
│  • Risk Assessment Capability                                        │
│                                                                      │
│  Data ABBs:                                                          │
│  • Customer Data Service                                             │
│  • Transaction Data Repository                                       │
│  • Reference Data Management                                         │
│                                                                      │
│  Application ABBs:                                                   │
│  • Identity Management Service                                       │
│  • Workflow Engine                                                   │
│  • API Gateway                                                       │
│                                                                      │
│  Technology ABBs:                                                    │
│  • Container Platform                                                │
│  • Message Queue Service                                             │
│  • Database Service                                                  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### SBB - Solution Building Block（解决方案构建块）

ABB 的具体实现，指定产品和技术。

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SBB 示例（对应上述 ABBs）                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ABB: Container Platform                                             │
│  SBBs:                                                               │
│  • Kubernetes on AWS EKS                                             │
│  • Docker + Kubernetes on Azure AKS                                  │
│  • OpenShift Container Platform                                      │
│                                                                      │
│  ABB: Message Queue Service                                          │
│  SBBs:                                                               │
│  • Apache Kafka                                                      │
│  • RabbitMQ                                                          │
│  • AWS SQS                                                           │
│                                                                      │
│  ABB: API Gateway                                                    │
│  SBBs:                                                               │
│  • Kong Gateway                                                      │
│  • AWS API Gateway                                                   │
│  • Azure API Management                                              │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## 视图和视角

### 核心视角（Viewpoints）

| 视角 | 用途 | 利益相关者 |
|------|------|-----------|
| Business Process Viewpoint | 展示业务流程和关联 | 业务分析师、流程负责人 |
| Application Behavior Viewpoint | 展示应用行为和交互 | 应用架构师、开发者 |
| Technology Deployment Viewpoint | 展示技术部署情况 | 技术架构师、运维人员 |
| Capability Map Viewpoint | 展示业务能力及其关系 | 高管、战略规划人员 |
| Information Map Viewpoint | 展示信息流动和存储 | 数据架构师、信息管理人员 |
| Migration Viewpoint | 展示迁移路径和阶段 | 项目经理、架构师 |

### 视图类型

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Architecture Views                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Strategic Views:                                                    │
│  ├── Business Model Canvas                                           │
│  ├── Capability Heat Map                                             │
│  └── Strategic Roadmap                                               │
│                                                                      │
│  Business Views:                                                     │
│  ├── Business Process Model                                          │
│  ├── Organization Chart                                              │
│  ├── Value Stream Map                                                │
│  └── Business Service Catalog                                        │
│                                                                      │
│  Information System Views:                                           │
│  ├── Application Landscape                                           │
│  ├── Data Flow Diagram                                               │
│  ├── Integration Map                                                 │
│  └── Application/Data Matrix                                         │
│                                                                      │
│  Technology Views:                                                   │
│  ├── Infrastructure Diagram                                          │
│  ├── Network Topology                                                │
│  ├── Deployment Diagram                                              │
│  └── Technology Standards Matrix                                     │
│                                                                      │
│  Cross-Cutting Views:                                                │
│  ├── Principles Catalog                                              │
│  ├── Standards Catalog                                               │
│  ├── Gap Analysis Matrix                                             │
│  └── Transition Architecture Roadmap                                 │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## 架构原则

### 原则结构

每个架构原则包含以下要素：

| 要素 | 描述 |
|------|------|
| Name（名称） | 简短的原则标题 |
| Statement（声明） | 原则的正式描述 |
| Rationale（依据） | 为什么采用这个原则 |
| Implications（影响） | 原则对架构的具体影响 |

### 示例原则

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Architecture Principle Example                    │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Name: Technology Independence                                       │
│  技术独立性                                                          │
│                                                                      │
│  Statement:                                                          │
│  架构设计应独立于特定技术和产品，使业务不被锁定于特定供应商。             │
│                                                                      │
│  Rationale:                                                          │
│  • 降低供应商锁定风险                                                 │
│  • 提高技术选型灵活性                                                 │
│  • 便于技术迁移和升级                                                 │
│                                                                      │
│  Implications:                                                       │
│  • 使用标准化协议和接口                                               │
│  • 采用开放标准                                                       │
│  • 设计抽象层隔离具体技术                                             │
│  • 避免深度集成特定产品专有功能                                        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## 架构治理

### 治理框架

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Architecture Governance Framework                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Governance Principles                     │   │
│  │   • Accountability  • Transparency  • Consistency            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Governance Organization                   │   │
│  │                                                               │   │
│  │   Architecture Board ──► Architecture Review Board           │   │
│  │         │                         │                           │   │
│  │         ▼                         ▼                           │   │
│  │   EA Team ◄────────────► Domain Architecture Teams           │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Governance Processes                      │   │
│  │                                                               │   │
│  │   • Architecture Compliance Review                           │   │
│  │   • Architecture Exception Process                           │   │
│  │   • Architecture Change Management                           │   │
│  │   • Architecture Communication                               │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 合规评审清单

| 检查项 | 描述 |
|--------|------|
| 原则符合性 | 是否遵循架构原则 |
| 标准符合性 | 是否使用批准的技术标准 |
| 参考架构一致性 | 是否与参考架构对齐 |
| 安全符合性 | 是否满足安全要求 |
| 可重用性 | 是否考虑组件重用 |
| 可互操作性 | 是否支持系统互操作 |

## 架构库

### Architecture Repository 结构

```
Architecture Repository
├── Architecture Metamodel
│   └── Content Metamodel Definition
├── Architecture Capability
│   ├── Skills Matrix
│   ├── Role Definitions
│   └── Training Materials
├── Architecture Landscape
│   ├── Baseline Architecture
│   │   ├── Business Architecture
│   │   ├── Data Architecture
│   │   ├── Application Architecture
│   │   └── Technology Architecture
│   └── Target Architecture
│       ├── Business Architecture
│       ├── Data Architecture
│       ├── Application Architecture
│       └── Technology Architecture
├── Standards Information Base
│   ├── Technology Standards
│   ├── Product Information
│   └── Vendor Information
├── Reference Library
│   ├── Reference Models
│   ├── Patterns
│   └── Templates
├── Governance Log
│   ├── Decision Log
│   ├── Compliance Assessments
│   └── Dispensations
└── Architecture Requirements Repository
    ├── Requirements
    ├── Constraints
    └── Assumptions
```

## 最佳实践

### 1. ADM 迭代应用

```
