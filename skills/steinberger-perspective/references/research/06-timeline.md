# Peter Steinberger 完整时间线

> 调研时间：2026-06-05
> 信息来源：个人博客、GitHub、Twitter/X、技术媒体采访、Y Combinator 访谈、TED 演讲
> 可信度：⭐⭐⭐⭐⭐（一手来源为主）

---

## 人物概览

| 字段 | 内容 |
|------|------|
| 全名 | Peter Steinberger |
| 网名 | @steipete |
| 国籍 | 奥地利 |
| 出生 | 约 1987 年（2021 年退休时约 34 岁） |
| 教育 | 维也纳工业大学（TU Wien）— 软件工程 |
| 职业 | PSPDFKit 创始人、OpenClaw 创始人、OpenAI 工程师 |
| 标签 | iOS 传奇开发者、SDK 工匠、AI Agent 先驱 |

---

## 详细时间线

### 🎓 成长期

| 时间 | 事件 | 备注 |
|------|------|------|
| ~14 岁 | 开始编程 | 自述"对构建东西有近乎痴迷的冲动" |
| 大学期间 | 就读维也纳工业大学（TU Wien） | 软件工程专业 |
| 大学期间 | 在 TU Wien 教授 iOS 和 Mac 开发课程 | 技术传播的起点 |
| 毕业后 | 获得硅谷工作机会 | 因 H-1B 签证等待超过半年 |

### 🚀 PSPDFKit 时代（2011–2021）

| 时间 | 事件 | 意义 |
|------|------|------|
| **2011** | 等待签证期间，开发 PSPDFKit 第一版 | 发现 iPad 上 PDF 体验差，从零开始写 PDF 渲染引擎 |
| 2011 | PSPDFKit 作为个人项目上线 | "几乎从第一天起就实现盈利" |
| 2011–2021 | 持续迭代 10 年 | 从 iOS 扩展到 macOS、Android、Web |
| ~2015 | 团队扩展至约 70 人 | 完全白手起家，无外部融资 |
| 持续 | 客户包括 Apple、Dropbox、SAP、大众汽车、迪士尼、IBM | 代码运行在超 10 亿台设备上 |
| 持续 | 成为 iOS 开发社区最有影响力的人物之一 | GitHub 上数百个开源项目 |
| **2021-10** | Insight Partners 以超 **1 亿欧元**投资 PSPDFKit | Steinberger 出售大部分股份，套现约 1 亿欧元 |
| 2021 | **退休**，转为顾问角色 | 经历 13 年高强度创业后燃尽（burnout） |

### 😴 退休期（2021–2025）

| 时间 | 事件 | 意义 |
|------|------|------|
| 2021–2024 | 从公众视野消失约 3 年 | 专注于恢复和个人生活 |
| ~2024 | 开始关注 AI 领域 | 从技术观察者转向实践者 |
| 2025 | 开始探索 AI 编程工作流 | 在博客上记录 AI 开发实践 |

### 🦞 OpenClaw 时代（2025–至今）

| 时间 | 事件 | 意义 |
|------|------|------|
| **2025-11-24** | 在 Mac Mini 上写下 OpenClaw 第一行代码 | 项目代号 Clawdbot |
| 2025-12 | 项目快速增长 | 开发者社区开始关注 |
| **2026-01 初** | Clawdbot 正式开源发布 | GitHub Star 数爆发式增长 |
| 2026-01-26 | 全球开发者疯狂传播 | 被称为"GitHub 史上增长最快的项目" |
| **2026-01-27** | Anthropic 要求更名（商标问题） | Clawdbot → **Moltbot**（"蜕皮"之意） |
| **2026-01-28** | 仅一天后再次更名 | Moltbot → **OpenClaw**（最终定名） |
| 2026-01-29 | 接受首个深度专访 | 分享创业经历和技术理念 |
| 2026-02 中旬 | GitHub Star 超 20 万 | 成为开源史上增长最快的项目之一 |
| **2026-02-15** | Sam Altman 宣布 Peter 加入 OpenAI | 负责推进下一代个人智能代理技术 |
| 2026-02 | 接受 Y Combinator 深度专访 | 预言"本地 AI 智能体将灭掉 80% 的 App" |
| 2026-03 | OpenClaw 生态爆发 | ClawHub 技能市场、社区贡献大量 Skill |
| 2026-04 | 站上 TED 舞台 | 演讲主题：倦怠、龙虾和 AI Agent |
| 2026-04 | NVIDIA 发布 NemoClaw | 基于 OpenClaw 的企业级 AI Agent 方案 |
| 2026-05 | OpenClaw 持续迭代 | 支持 macOS、Windows、Linux、iOS、Android 全平台 |

---

## 技术栈演进

```
2011-2015: Objective-C → iOS SDK
2015-2018: Objective-C + Swift 混合 → 跨平台扩展
2018-2021: Swift 为主 → iOS + macOS + Android + Web (PSPDFKit 全平台)
2021-2025: 退休，技术观察期
2025-2026: Node.js + TypeScript → OpenClaw (全平台 AI Agent)
           - macOS 原生（Swift/AppKit）
           - Windows Hub（Electron/Tauri）
           - Linux 服务端
           - iOS/Android 节点（原生）
```

---

## OpenClaw 架构中的技术决策（Windows 相关）

### 1. 跨平台策略：Gateway + Node 架构

Peter 的核心设计决策：**不在每个平台上重写核心逻辑**。

```
Gateway（控制平面）
├── macOS Node（原生 Swift）
├── Windows Hub（Electron 桌面应用）
├── Linux Node（服务端）
├── iOS Node（原生 Swift）
└── Android Node（Kotlin）
```

**Windows 特殊考量：**
- Windows Hub 作为 Companion App，提供：设置向导、状态托盘、聊天界面、节点模式、本地 MCP 模式
- 底层依赖 Node.js 22.x 运行时
- 通过 npm 全局安装：`npm install -g openclaw@latest`
- 使用 PowerShell 管理服务（`openclaw gateway start/stop`）

### 2. Windows 部署哲学

Peter 的理念：**2GB 内存就能跑，一行命令就能装**。

- 不依赖 Docker（原生 Node.js 运行）
- 最小依赖：Node.js + Git
- 支持 nvm 版本管理
- 开机自启通过 Windows 计划任务实现

### 3. 跨平台一致性

```python
# Peter 的设计原则（从代码推断）
- Gateway 是唯一的控制平面（ws://127.0.0.1:18789）
- 所有平台共享同一套 Agent 逻辑
- 平台差异只在 Node 层（输入/输出/权限）
- 频道适配器处理平台差异（WhatsApp/Telegram/Discord 等）
```

### 4. Windows 特有能力

| 能力 | 实现方式 |
|------|----------|
| 桌面控制 | 通过 Windows Accessibility API |
| 文件操作 | Node.js fs 模块（跨平台） |
| 浏览器控制 | CDP（Chrome DevTools Protocol） |
| 语音唤醒 | Windows 原生音频 API |
| 系统通知 | Windows Toast Notification |
| 开机自启 | Windows Task Scheduler / 服务 |

---

## 关键思想转折点

| 转折点 | 时间 | 影响 |
|--------|------|------|
| 签证等待 → 创业 | 2011 | 被动创业，发现了 PDF 市场空白 |
| 10 年创业 → 燃尽退休 | 2021 | "经营了 13 年，彻底燃尽" |
| 退休 3 年 → AI 浪潮回归 | 2025 | "AI 让我重新找到了编程的乐趣" |
| 周末项目 → 全球爆火 | 2026-01 | "我差点把这个项目删了" |
| 独立开发者 → OpenAI 工程师 | 2026-02 | 从个人项目到全球最大 AI 公司 |

---

## 最近 12 个月动态（2025-06 至 2026-06）

| 时间 | 动态 |
|------|------|
| 2025-07~10 | 探索 AI 编程工作流，在博客记录实践 |
| 2025-11-24 | 写下 OpenClaw 第一行代码 |
| 2025-12 | 项目快速迭代，社区开始关注 |
| 2026-01 | 开源发布 → 三天更名两次 → GitHub 爆发 |
| 2026-02-15 | 加入 OpenAI |
| 2026-03 | Y Combinator 专访、"80% App 将消亡"预言 |
| 2026-04 | TED 演讲、NVIDIA NemoClaw 合作 |
| 2026-05 | OpenClaw 持续迭代，全平台稳定 |

---

## 信息来源

| 来源 | 类型 | URL |
|------|------|-----|
| steipete.me（个人博客） | 一手 | https://steipete.me/posts |
| GitHub @steipete | 一手 | https://github.com/steipete |
| Twitter/X @steipete | 一手 | https://x.com/steipete |
| Y Combinator 访谈 | 一手 | https://blog.csdn.net/wo1141786653/article/details/158768627 |
| TED 演讲 | 一手 | https://www.yeyulingfeng.com/531753.html |
| PSPDFKit 官方博客 | 一手 | https://www.nutrient.io/blog/ |
| OpenClaw GitHub | 一手 | https://github.com/openclaw/openclaw |
| Grokipedia | 二手 | https://grokipedia.com/page/peter-steinberger |
| IQ.wiki | 二手 | https://iq.wiki/zh/wiki/peter-steinberger/milestones |
