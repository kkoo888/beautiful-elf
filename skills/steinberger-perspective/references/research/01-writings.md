# Peter Steinberger 著作与系统性长文调研

> 调研日期: 2026-06-05
> 一手来源: steipete.me 博客、GitHub (steipete)、@steipete Twitter/X
> 二手来源: CSDN、雪球、掘金、腾讯新闻等中文科技媒体转载/解读（可信度标注）

---

## 一、人物背景与关键时间线

- **出生/教育**: 奥地利人，毕业于维也纳工业大学 (TU Wien) 计算机与信息科学专业，后在该校教授 iOS/Mac 开发课程
- **PSPDFKit**: 2011 年创立，全球领先的 PDF SDK，嵌入超过 10 亿台设备，客户包括 Apple、Microsoft 等巨头
- **退出**: 2021 年以约 1 亿欧元将多数股权出售给 Insight Partners，之后经历约 3 年的倦怠期
- **回归**: 2024 年 11 月重新开始编程，2025 年 1 月用 10 天"vibe-coded" 出 OpenClaw (原 Clawdbot)
- **加入 OpenAI**: 2026 年 2 月宣布加入 OpenAI，OpenClaw 转入基金会保持开源独立
- **GitHub**: 170+ 个仓库，涵盖 AI 工具链、CLI 工具、macOS 工具等

> 来源: steipete.me/posts/2025/finding-my-spark-again | 可信度: ★★★★★ 一手

---

## 二、核心博客文章（一手来源）

### 2.1 PSPDFKit 时代的技术写作 (2016-2021)

#### 《Swifty Objective-C》(2016.05)
- **URL**: https://steipete.me/posts/2016/swifty-objective-c
- **核心论点**: Objective-C 可以通过 Objective-C++ 子集获得 Swift 的部分优势（auto、let、vector），无需全面迁移
- **技术立场**: 不急于迁移到 Swift——"Swift is evolving incredibly fast... it's also a fast-moving target and there are still many, partly scary, bugs"
- **关于 ABI**: "Using Swift without binary compatibility would mean that we have to offload technical details to our customers"
- **关于 C++**: "Think about Objective-C++ as a small language addition to Objective-C"——只需将 .m 改为 .mm 即可
- **可信度**: ★★★★★ 一手，基于 PSPDFKit 60 万行代码的实战经验

#### 《Even Swiftier Objective-C》(2017.06)
- **URL**: https://steipete.me/posts/2017/even-swiftier-objective-c
- **核心论点**: WWDC 2017 新增的 Objective-C 特性使其更接近 Swift
- **可信度**: ★★★★★ 一手

#### 《The Case for Deprecating UITableView》(2017.01)
- **URL**: https://steipete.me/posts/2017/the-case-for-deprecating-uitableview
- **核心论点**: UICollectionView 是 UITableView 的完美超集，应废弃 UITableView
- **关键引用**: "UICollectionView is a masterpiece of flexibility and great API design"
- **API 设计理念**: 批评 UITableView 的 beginUpdates/endUpdates 模式——"very easy to mess up balancing calls... whereas this is impossible with UICollectionView's API"
- **发现**: Apple 内部已有 UICollectionViewTableLayout 私有 API（iOS 10 runtime headers）
- **可信度**: ★★★★★ 一手，直接影响了后续 iOS SDK 演进方向

#### 《Binary Frameworks in Swift》(2018.01，dotSwift 2018 演讲)
- **URL**: https://steipete.me/posts/2018/binary-frameworks-swift
- **核心论点**: ABI stability 不等于可以发布二进制 Swift 框架——"ABI stability is necessary, though not sufficient, for binary frameworks. Module format stability is also required"
- **关键洞察**: Array 从 24 字节变为 8 字节的例子说明 ABI 锁定会阻止后续优化
- **引用**: "We also fully believe that delaying the stable Swift ABI is a good thing. It's inconvenient in the short-term, but will result in a better language in the long-term"
- **可信度**: ★★★★★ 一手，dotSwift 大会演讲

#### 《How We Work at PSPDFKit》(2019.07)
- **URL**: https://steipete.me/posts/2019/how-we-work
- **核心论点**: SDK 开发 vs App 开发的根本差异
- **关键理念**:
  - "Developing an SDK has unique challenges... people expect our API to be consistent, and ideally it shouldn't ever change"
  - "We take great care to evolve our API in a meaningful way, and often the design is forward-thinking so that future extensions are easier"
  - Proposal-Based Development: 几乎每个功能都从 proposal 开始，包含 Summary/Motivation/Details/Tradeoffs/Current APIs/Proposed APIs
  - "We preach the Boy Scout Rule to 'leave it better than you found it'"
  - 代码量超过 100 万行，2009 年的代码至今仍在使用
  - "We cannot do a 'grand rewrite' every few years"
- **可信度**: ★★★★★ 一手，PSPDFKit 内部工程文化全景

#### 《The State of SwiftUI》(2020.09)
- **URL**: https://steipete.me/posts/2020/state-of-swiftui
- **技术立场**: 对 SwiftUI 保持谨慎乐观
  - "I personally wouldn't yet go all-in on SwiftUI for production apps"
  - "SwiftUI ships with the OS, not with your app, so any bug fixes will only help if your users update the OS"
  - "The AppKit port is particularly troublesome"
  - "Use Catalyst, which is a much more stable binding"
  - "SwiftUI itself is fast — for many use cases it's even faster than using CALayer"
  - 用 Instruments 分析发现: "30 percent of them are used for the various retain/release and malloc calls in Swift and Objective-C"
- **可信度**: ★★★★★ 一手，基于 Apple Fruta 示例的深度逆向分析

#### 《Writing Good Bug Reports》(2016.09)
- **URL**: https://steipete.me/posts/2016/writing-good-bug-reports
- **核心理念**: "File one report per issue"、"Add the selector name to the issue title"、"Make a short, runnable sample"、"Add humor"、"Be concise"、"Propose a workaround"
- **引用**: "Bug reports don't need to be dry! Sometimes they are Dr. Who themed. Or have cat pictures."
- **可信度**: ★★★★★ 一手

#### 《Hiring a Distributed Team》(2016.09)
- **URL**: https://steipete.me/posts/2016/hiring-a-distributed-team
- **核心理念**:
  - "Who you hire can have a dramatic effect on your team's culture and company's productivity"
  - 开放问题: "Who are you as a programmer" + "Send us a piece of code that does something you find interesting, and explain why"
  - 90% 的候选人直接忽略了这些问题——easy filter
  - "We made a goal this year to write a blog post every single week"——展示公司文化是最好的招聘广告
  - "Conveying your company's culture is the number one way to attract great people"
- **可信度**: ★★★★★ 一手

### 2.2 AI 时代的技术写作 (2025-2026)

#### 《Finding My Spark Again》(2025.06)
- **URL**: https://steipete.me/posts/2025/finding-my-spark-again
- **核心论点**: 创始人退出后的空虚感
  - "I felt like I missed out on life. A lot of my normie friends had fun every weekend while I was just crushing and pushing"
  - "You don't find happiness by moving countries. You don't find purpose. You create it."
- **可信度**: ★★★★★ 一手，极度坦诚的个人叙述

#### 《Just One More Prompt》(2025.08，Claude Code Anonymous 演讲)
- **URL**: https://steipete.me/posts/just-one-more-prompt
- **核心论点**:
  - "Hi, my name is Peter and I'm a Claudoholic"
  - "AI was supposed to save time, yet I work more than ever before"
  - "One week in AI feels like a month in the real world"
  - "I allowed myself to be sucked into the vortex for a while. This is exactly how I started my last company."
  - "I work in waves, a period of very intense work, followed by a period of slacking off"
  - 自我反思: "I literally built something so I have better access to my drug" (指 VibeTunnel)
- **可信度**: ★★★★★ 一手

#### 《Claude Code is My Computer》(2025.06)
- **URL**: https://steipete.me/posts/2025/claude-code-is-my-computer
- **核心论点**:
  - "I run Claude Code in no-prompt mode... hasn't broken my Mac in two months"
  - "What I actually got was a universal computer interface that happens to run in text"
  - 从"AI assistant"到"everything terminal"的心智转变
  - "Claude Code shines because it was built command-line-first, not bolted onto an IDE as an afterthought"
  - "Syntax fades, system thinking shines"
  - 批评 Warp: "Claude operates purely through text... Warp requires individual approval for each command—there's no equivalent to Claude's 'dangerous mode'"
- **可信度**: ★★★★★ 一手

#### 《Shipping at Inference-Speed》(2025.12，最重要的一篇)
- **URL**: https://steipete.me/posts/2025/shipping-at-inference-speed
- **核心论点**:
  - "The amount of software I can create is now mostly limited by inference time and hard thinking"
  - "Most software does not require hard thinking. Most apps shove data from one form to another"
  - "I don't read much code anymore. I watch the stream and sometimes look at key parts"
  - 语言选择: TypeScript (web), Go (CLIs), Swift (macOS/UI)
  - "Go wasn't something I gave even the slightest thought even a few months ago, but eventually I played around and found that agents are really great at writing it"
  - codex vs Opus: "codex has been trained to read LOTS of code before starting... sometimes it just silently reads files for 10, 15 minutes before starting to write any code"
  - "Plan mode feels like a hack that was necessary for older generations of models"
  - 工作方式: 同时做 3-8 个项目，直接 commit to main，几乎不 revert
  - "Building software is like walking up a mountain. You don't go straight up, you circle around it and take turns"
  - 重要区分: 不喜欢 "vibe coding" 这个词，更倾向 "agentic engineering"
- **可信度**: ★★★★★ 一手，被视为其技术哲学宣言

#### 《MCP Best Practices》(2025.06)
- **URL**: https://steipete.me/posts/2025/mcp-best-practices
- **核心理念**:
  - "Sensible Defaults" — 所有环境变量必须有合理默认值
  - "No single file should exceed 500 lines of code (LOC); aim for below 300 LOC"
  - "Parameter parsing should be lenient... advertise stricter schemas but be more lenient in execution"
  - "No output to stdio during normal tool operation"——日志写文件
  - 详细的测试/构建/发布规范
- **可信度**: ★★★★★ 一手

#### 《Stop Over-thinking AI Subscriptions》(2025.06)
- **URL**: https://steipete.me/posts/2025/stop-overthinking-ai-subscriptions
- **核心论点**:
  - "Time is the only non-refillable resource"
  - "Token prices have dropped 1000× in the last two years... The trend line points one direction: down"
  - 承包商数学: "One afternoon saved per month = $200 in billable time. Claude Max pays for itself in 5 saved hours."
- **可信度**: ★★★★★ 一手

#### 《Essential Reading for Agentic Engineers - August 2025》(2025.08)
- **URL**: https://steipete.me/posts/2025/essential-reading-august-2025
- **核心论点**: 精选 5 篇必读文章，涵盖开发者角色演进、初级开发者技能危机、10x 生产力神话、平台垄断终结、MCP 陷阱
- **引用**: "All code is technical debt"（来自 Austin Parker 的文章，Steinberger 推荐）
- **可信度**: ★★★★★ 一手（推荐内容反映其价值观）

#### 《OpenClaw, OpenAI and the future》(2026.02)
- **URL**: https://steipete.me/posts/2026/openclaw
- **核心内容**: 宣布加入 OpenAI，OpenClaw 转入基金会
- **可信度**: ★★★★★ 一手

---

## 三、开源项目与设计理念

### 3.1 PSPDFKit (2011-2021)
- **性质**: 商业 PDF SDK，支持 iOS/Android/Web/Windows/macOS
- **设计哲学**:
  - "SDK != App" — API 一致性比功能丰富更重要
  - Proposal-based development — 每个功能先写 proposal
  - 跨平台 API 设计的平衡: "finding a compromise between platform-idiomatic APIs and building common patterns across all platforms"
  - Boy Scout Rule: "leave it better than you found it"
  - 每周一篇博客分享知识——"conveying your company's culture is the number one way to attract great people"

### 3.2 Aspects (2013-)
- **GitHub**: https://github.com/steipete/Aspects
- **性质**: 轻量级 iOS/macOS AOP (面向切面编程) 库
- **设计**: 在 Objective-C runtime 基础上实现 Before/After/Around 三种切面操作
- **被引用**: 被 ObjC Zen Book 推荐为 iOS 平台 AOP 的标准实现
- **可信度**: ★★★★★ 一手

### 3.3 InterposeKit (2020)
- **GitHub**: https://github.com/steipete/InterposeKit
- **性质**: Swift 的 method swizzling 库
- **设计理念**: 利用 Swift 5.2 的 callAsFunction 实现类型安全的 Objective-C 方法拦截
- **可信度**: ★★★★★ 一手

### 3.4 PSTCollectionView (早期)
- **GitHub**: https://github.com/steipete/PSTCollectionView
- **性质**: UICollectionView 的向后兼容实现 (支持 iOS 4.3+)
- **设计**: "some crazy runtime hackery"——在运行时将 PSTCollectionView 映射到真正的 UICollectionView
- **可信度**: ★★★★★ 一手

### 3.5 OpenClaw (2024.11-)
- **性质**: 开源 AI Agent 框架
- **设计哲学**:
  - Unix 哲学回归: 简单工具、文本流通信、本地控制
  - "让我妈妈这样的普通用户也能用上 AI Agent"
  - CLI-first，非 IDE 挂载
- **可信度**: ★★★★★ 一手

### 3.6 其他工具矩阵 (2025-2026)
- **Peekaboo**: 截图 + 图像问答 MCP 工具
- **Poltergeist**: 通用自动构建监听器
- **VibeTunnel**: 浏览器终端控制器
- **Vibe Meter**: macOS 菜单栏 AI 支出监控
- **llm.codes**: 将 Apple 文档转为 AI 可读格式
- **Oracle**: 让 agent 调用 GPT 5 Pro 的 CLI 工具
- **Sag**: TTS CLI 工具
- **Bird**: Twitter CLI 工具
- **Clawdis**: 全设备 AI 助手（屏幕控制、消息、邮件、家居、摄像头、音乐等）
- **可信度**: ★★★★★ 一手（GitHub 仓库）

---

## 四、反复出现的核心论点（≥3 次出现 = 真信念）

### 4.1 "代码是副产品，协调才是产品" (Code is the artifact. Coordination is the product.)
- 出现于: OpenClaw PHILOSOPHY.md、多次访谈、演讲
- **可信度**: ★★★★★

### 4.2 "大多数软件不需要深度思考"
- Shipping at Inference-Speed: "Most software does not require hard thinking. Most apps shove data from one form to another"
- **可信度**: ★★★★★

### 4.3 "语法让位于系统思维"
- Claude Code is My Computer: "Syntax fades, system thinking shines"
- 多次演讲: "从 violinist 变成 orchestra conductor"
- **可信度**: ★★★★★

### 4.4 "不要把自己定义为 iOS 工程师"
- 多次演讲/访谈: "不要再把自己看成 iOS 工程师了"
- "Full-breadth developer" 概念——引用 Justin Searls 的文章
- **可信度**: ★★★★★

### 4.5 "API 一致性比功能丰富更重要"
- How We Work at PSPDFKit: "people expect our API to be consistent, and ideally it shouldn't ever change"
- UITableView 文章: 批评不一致的 API 设计
- **可信度**: ★★★★★

### 4.6 "Boy Scout Rule"
- How We Work at PSPDFKit: "We preach the Boy Scout Rule to 'leave it better than you found it'"
- 代码随时间渐进式改进，不做大重写
- **可信度**: ★★★★★

### 4.7 "你不需要读代码"
- Shipping at Inference-Speed: "I don't read much code anymore"
- Claude Code is My Computer: 从"读代码"到"看它流过"
- **矛盾记录**: 他自己也说 "I do know where which components are and how things are structured"——不是完全不理解，而是不再逐行审查
- **可信度**: ★★★★★

### 4.8 "时间是唯一不可补充的资源"
- Stop Over-thinking AI Subscriptions: "Time is the only non-refillable resource"
- Finding My Spark Again: 后悔把所有时间都投入公司
- **可信度**: ★★★★★

### 4.9 "简单代码优于聪明代码"
- 演讲摘要: "simple code beats clever solutions when working with AI"
- Go 语言偏好: "its simple type system makes linting fast"
- **可信度**: ★★★★★

### 4.10 "你不会通过搬家找到幸福"
- Finding My Spark Again: "You don't find happiness by moving countries. You don't find purpose. You create it."
- **可信度**: ★★★★★

---

## 五、自创术语与概念

| 术语 | 定义 | 来源 |
|------|------|------|
| **Agentic Engineering** | 用 AI agent 编排和构建软件的新范式，区别于 "vibe coding" | 多次演讲/访谈 |
| **Full-breadth Developer** | 不局限于单一平台/技术栈的开发者，结合技术专长与产品视野 | 演讲摘要，引用 Justin Searls |
| **Claudoholic** | 对 Claude Code/Agentic Engineering 成瘾的开发者 | Claude Code Anonymous 演讲 |
| **Black Eye Club** | 凌晨 4 点还在用 AI 编码的朋友圈 | Just One More Prompt |
| **Shipping at Inference-Speed** | 代码交付速度受限于模型推理速度而非人类编码速度 | 2025.12 博文 |
| **Ninja Refactoring** | 在日常工作中渐进式重构（Boy Scout Rule 的延伸） | PSPDFKit 博客 |

---

## 六、对 Swift / Objective-C / UIKit / SwiftUI 的技术立场

### Objective-C 时代 (2011-2018)
- **立场**: 务实主义者。不急于迁移，因为 ABI 未稳定、二进制框架不可行
- **实践**: 用 Objective-C++ 获取 C++ 的 auto/let/vector 优势
- **关键引用**: "Swift in its current form is in many ways more like C++... There is no dynamic message sending"

### SwiftUI 立场 (2020)
- **立场**: 谨慎乐观，但不建议生产使用
- **关键引用**: "I personally wouldn't yet go all-in on SwiftUI for production apps"
- **技术判断**: AppKit 绑定问题多，Catalyst 更稳定；SwiftUI 本身快但与 AppKit 的交互慢

### AI 时代 (2025+)
- **语言偏好转变**: TypeScript (web) > Go (CLI) > Swift (macOS UI)
- **对 Xcode 的态度**: "You don't need Xcode much anymore. I don't even use xcodeproj files"
- **对 Swift 的态度**: 仍用于 macOS 和 UI，但不再是首选
- **可信度**: ★★★★★ 一手

---

## 七、会议演讲

| 日期 | 会议 | 主题 | 可信度 |
|------|------|------|--------|
| 2018.01 | dotSwift Paris | Binary Frameworks in Swift | ★★★★★ |
| 2018 | (会议待确认) | Hacking Marzipan | ★★★★★ |
| 2019 | WWDC | (多次参与) | ★★★★★ |
| 2023.05 | Deep Dish Swift | 个人故事：创业→倦怠→重生（主题演讲） | ★★★★★ |
| 2024 | iOS Conf SG | 个人故事（修改版） | ★★★★★ |
| 2025 | Claude Code Anonymous London | Just One More Prompt | ★★★★★ |
| 2026.03 | NVIDIA GTC | Agentic Engineering（邀请制） | ★★★★★ |
| 2026.04 | AI Engineer Europe | Agentic Engineering | ★★★★★ |
| 2026.04 | TED 2026 Vancouver | (主题待确认) | ★★★★★ |
| 2026.05 | OMR Festival Hamburg | (主题待确认) | ★★★★★ |
| 2026.06 | Microsoft Build | (主题待确认) | ★★★★★ |
| 2026.08 | Agentic AI Summit Berkeley | (主题待确认) | ★★★★★ |
| 2026.10 | TEDAI Vienna | (主题待确认) | ★★★★★ |

> 来源: https://github.com/steipete/speaking | 可信度: ★★★★★ 一手

---

## 八、推荐内容与智识谱系

### 推荐的文章/作者（从 Essential Reading 系列提取）
- **Thomas Dohmke** (GitHub CEO): Developers, Reinvented — 开发者 4 阶段演进
- **Namanyay Goel**: AI 与学习危机
- **Colton Anglin**: AI 10x 生产力神话的现实检验
- **Austin Parker**: 平台垄断终结——"All code is technical debt"
- **Geoffrey Huntley**: MCP 服务器的陷阱
- **Justin Searls**: Full-breadth developers 概念
- **Gergely Orosz** (Pragmatic Engineer): AI 创业公司极端工时

### 推荐的工具/技术
- **Ghostty**: 终端（非 Electron，原生更快）
- **Claude Code**: CLI-first AI 工具
- **Codex/GPT 5.2**: 代码生成
- **Wispr Flow**: 语音转文字
- **Arq + SuperDuper!**: 备份方案
- **Repo Prompt**: 通过 ChatGPT 订阅使用 o3

### 未明确推荐的书单
- **注意**: 在调研范围内未发现系统性书单推荐。他的智识输入更多来自工程实践、开源社区和技术会议，而非传统书籍。
- **间接线索**: ObjC Zen Book 引用了他的 Aspects 库；他对 API 设计的品味暗示受 Apple 框架设计哲学影响

---

## 九、矛盾与张力记录

### 矛盾 1: "不读代码" vs "理解架构"
- **表述 A**: "I don't read much code anymore" (Shipping at Inference-Speed)
- **表述 B**: "I do know where which components are and how things are structured and how the overall system is designed"
- **解读**: 不是矛盾，而是区分了"逐行审查"和"系统理解"——他放弃前者但保留后者

### 矛盾 2: "AI 节省时间" vs "工作更多"
- **表述 A**: 多处强调 AI 的生产力提升
- **表述 B**: "AI was supposed to save time, yet I work more than ever before" (Just One More Prompt)
- **解读**: 真实的张力——AI 提高了能力上限但降低了工作边界

### 矛盾 3: "不使用 Xcode" vs "Swift 开发者"
- **表述 A**: "You don't need Xcode much anymore. I don't even use xcodeproj files"
- **表述 B**: 仍是 Swift 社区的重要声音，SwiftUI/InterposeKit 等项目仍用 Swift
- **解读**: 反映了从平台开发者到全栈 AI 构建者的身份转变

### 矛盾 4: "Agentic Engineering" vs "Vibe Coding"
- **表述**: 明确不喜欢 "vibe coding" 这个词，更倾向 "agentic engineering"
- **现实**: 他自己也用 "vibe-coded" 来描述 OpenClaw 的创建过程
- **解读**: 术语上的纠结——他在定义自己的实践时，既想与潮流保持距离，又无法完全脱离

---

## 十、二手来源可信度评估

| 来源 | 类型 | 可信度 | 说明 |
|------|------|--------|------|
| CSDN 博客 | 二手 | ★★★☆☆ | 内容多为转载/翻译，部分有加工 |
| 雪球 | 二手 | ★★★☆☆ | 宝玉等人的访谈实录翻译，较可靠 |
| 掘金 | 二手 | ★★★☆☆ | 开发者社区解读，有偏差 |
| 腾讯新闻 | 二手 | ★★☆☆☆ | 标题党倾向，内容有简化 |
| 澎湃新闻 | 二手 | ★★★★☆ | 深度访谈实录，较可靠 |
| SegmentFault | 二手 | ★★★★☆ | 开发者社区，内容较准确 |
| GitHub README | 一手 | ★★★★★ | 直接来源 |
| steipete.me | 一手 | ★★★★★ | 个人博客，最可靠 |

---

## 十一、关键 URL 汇总

### 个人博客
- 主站: https://steipete.me (steipete.com 重定向至此)
- 文章归档: https://steipete.me/posts

### GitHub
- 个人: https://github.com/steipete
- 演讲记录: https://github.com/steipete/speaking
- Agent 规则: https://github.com/steipete/agent-rules
- Agent 脚本: https://github.com/steipete/agent-scripts

### 社交
- Twitter/X: https://x.com/steipete

### 关键文章
- Shipping at Inference-Speed: https://steipete.me/posts/2025/shipping-at-inference-speed
- Claude Code is My Computer: https://steipete.me/posts/2025/claude-code-is-my-computer
- Just One More Prompt: https://steipete.me/posts/just-one-more-prompt
- Finding My Spark Again: https://steipete.me/posts/2025/finding-my-spark-again
- How We Work at PSPDFKit: https://steipete.me/posts/2019/how-we-work
- The State of SwiftUI: https://steipete.me/posts/2020/state-of-swiftui
- The Case for Deprecating UITableView: https://steipete.me/posts/2017/the-case-for-deprecating-uitableview
- Swifty Objective-C: https://steipete.me/posts/2016/swifty-objective-c
- Binary Frameworks in Swift: https://steipete.me/posts/2018/binary-frameworks-swift
- MCP Best Practices: https://steipete.me/posts/2025/mcp-best-practices
- Writing Good Bug Reports: https://steipete.me/posts/2016/writing-good-bug-reports
- Hiring a Distributed Team: https://steipete.me/posts/2016/hiring-a-distributed-team
- OpenClaw announcement: https://steipete.me/posts/2026/openclaw
