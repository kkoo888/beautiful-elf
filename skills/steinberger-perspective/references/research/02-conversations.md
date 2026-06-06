# Peter Steinberger — 长对话与即兴思考

> 调研时间：2026-06-05
> 调研范围：播客访谈、会议演讲、博客文章、Twitter/X 讨论、二手转述

---

## 一、播客与长访谈

### 1.1 The Pragmatic Engineer Podcast — "I ship code I don't read"（2026年1月）

- **来源**：[Pragmatic Engineer Newsletter](https://newsletter.pragmaticengineer.com/p/the-creator-of-clawd-i-ship-code) / [YouTube](https://youtu.be/8lF7HmQ_RgY)
- **可信度**：★★★★★（一手，有完整视频/transcript）
- **时长**：约114分钟，在伦敦录制
- **主持人**：Gergely Orosz

#### 核心即兴发言

**关于代码审查的死亡**：
> "Pull requests are dead, long live 'promot requests.'"（PR 已死，"提示词请求"万岁。）

他现在更关心生成代码的 prompt 而非代码本身。他会把别人的 PR 当作"意图表达"，标记 co-author 但很少直接合并。

**关于管理团队与放弃完美主义**：
> "Managing a dev team teaches you to let go of perfectionism: a skill important when working with agents today."（管理开发团队教会你放弃完美主义——这在今天与 AI agent 协作时至关重要。）

PSPDFKit 70+ 人的团队迫使他接受代码不会永远符合他的个人偏好。

**关于大多数代码的本质**：
> "Most code is boring data transformation — focus energy on system design instead."（大多数代码只是无聊的数据转换——把精力放在系统设计上。）

**关于 CI 的态度**（争议性表态）：
> "I don't care about CI."

他在本地通过 agent 跑测试，不愿等远程 CI 的 10 分钟延迟。

**关于开发者类型**：
> "Engineers who thrive with AI care about outcomes over implementation details."（在 AI 时代如鱼得水的工程师关心结果而非实现细节。）

他观察到喜欢解算法谜题的人在"AI-native"转型中挣扎，而喜欢 shipping 产品的人则表现出色。

**关于 PSPDFKit 如果今天重建**：
他暗示如果今天重新开始，架构会完全不同——更轻量、更依赖 AI agent 参与。

**关于"闭合环路"**：
> "Close the loop: AI agents must be able to verify their own work."（闭环：AI agent 必须能验证自己的工作。）

他设计系统让 agent 能自行编译、lint、执行和验证输出。

**关于 agent 管理**：
他同时运行 5-10 个 agent，花大量时间与 agent 来回讨论计划。他挑战 agent、调整、push back。满意后才启动执行，然后转向下一个。他偏好 Codex 因为它能做长时间运行的任务——Claude Code 总回来问问题让他分心。

**关于"故意模糊提示"**：
> "Under-prompt intentionally to discover unexpected solutions."（故意给模糊的提示来发现意想不到的解决方案。）

---

### 1.2 Lex Fridman Podcast #491（2025年2月）

- **来源**：[Lex Fridman 官网](https://lexfridman.com/peter-steinberger/) / [YouTube](https://youtube.com/watch?v=AcwK1Uuwc0U)
- **可信度**：★★★★★（一手，有完整视频）
- **时长**：约3小时

#### 核心即兴发言

**关于"Vibe Coding"这个词**：
> "I actually think vibe coding is a slur. I always tell people I do agentic engineering, and then maybe after 3:00 AM, I switch to vibe coding, and then I have regrets on the next day."（我觉得"氛围编程"是个贬义词。我总是跟人说我做的是"智能体工程"，也许凌晨三点以后我才切换到 vibe coding，然后第二天后悔。）

**关于代码库设计哲学的转变**：
> "I'm not building the code base to be perfect for me, but I wanna build a code base that is very easy for an agent to navigate."（我不再为了"我的完美"去构建代码库，而是要构建一个让 Agent 容易导航的代码库。）

**关于名字选择**：
> "Don't fight the name they pick, because it's most likely, like, in the weights, the name that's most obvious."（不要跟 AI 选的名字对着干，因为最明显的名字很可能就在模型权重里。）

**关于 Meta 和 OpenAI 的收购竞争**：
扎克伯格和同事 Ned 整整一周在玩 OpenClaw，不断给反馈。Peter 认为"别人真的在用你做的东西"是最大的认可。

**关于编程的未来**：
他称编程终将沦为"织毛衣"（knitting），暗示编程将变成一种手工爱好而非核心生产力。

---

### 1.3 Peter Yang 访谈（2026年2月，约40分钟）

- **来源**：[baoyu.io 翻译整理](https://baoyu.io/blog/2026/02/01/peter-steinberger-interview) / YouTube
- **可信度**：★★★★☆（一手视频，中文翻译为二手）
- **主持**：Peter Yang

#### 核心即兴发言

**关于一小时原型的故事**：
> "等到去年 11 月还没人做，我就想算了，我自己来。" 最初版本只是把 WhatsApp 接到 Claude Code 上。一个小时就搭完了。

**关于摩洛哥的自动修 bug**：
他在摩洛哥给朋友过生日时，拍了张 Twitter bug 报告的截图发到 WhatsApp。AI 读懂了推文，checkout 了 Git 仓库，修了 bug，提交了代码，然后在 Twitter 上回复说已经修好了。

**关于语音消息的"涌现能力"**：
他发了条语音消息，但他从没写过语音支持。AI 自己发现文件头是 Ogg Opus 格式，用 ffmpeg 转成 WAV，找到 OpenAI API key，用 curl 做了转录。

> "这也行？"

**关于 CLI 军团**：
他逆向了 Eight Sleep 的 API 控制床温，黑进了外卖平台的 API，建了 Google Places CLI、表情包 CLI。

**关于换技术栈的痛苦与解脱**：
> "从一个精通的技术栈换到另一个，过程很痛苦……然后有了 AI，这一切都消失了。你的系统级思维、架构能力、品味、对依赖的判断，这些才是真正有价值的。"
>
> "**突然之间我觉得自己什么都能建。语言不重要了，重要的是我的工程思维。**"

**关于 80% 的 App 会消失**：
> "如果你想想看，这个东西可能会取代你手机上 80% 的 app。"

**对复杂编排系统的猛烈批评**：
他把一个叫 Gastown 的编排系统戏称为"**Slop Town**"（垃圾镇）。

> "一个超复杂的编排器，同时跑十几二十个智能体……有观察者、监工、**市长**，我都不知道还有什么。"
>
> "这简直是终极的 Token 燃烧机。你让它跑一整晚，第二天早上得到的是终极垃圾（slop）。"

**对 RALPH 模式的批评**：
有人在 Twitter 上炫耀"全 RALPH 生成"的笔记 app。Peter 回复：是的，看起来就像 RALPH 生成的，没有正常人会这么设计。

**关于"虚荣指标"**：
> "我也让循环跑过 26 小时，当时很得意。但这是**虚荣指标**，毫无意义。能建一切不代表你应该建一切，也不代表它会是好的。"

**关于 Plan Mode**：
> "Plan mode 是 Anthropic 不得不加的拼凑方案，因为模型太冲动，一上来就跑去写代码。"

他偏好用自然语言对话来规划，而非依赖专门的 plan mode。

**关于品味的不可替代性**：
> "我不知道没有感受、没有品味参与的情况下，怎么能做出好东西。"

**把 PR 当作 prompt request**：
> "我把 pull request 当作 prompt request，它们传达的是意图……我宁可拿到意图，自己来做。"

**关于非技术用户也能贡献代码**：
他的前 PSPDFKit 联合创始人（一个前律师）现在也在给他发 PR。一个非技术朋友装了 OpenClaw 后开始发 pull request——这人这辈子从没发过 PR。

---

### 1.4 Lex Fridman 播客细节补充（来源：雪球整理）

- **来源**：[雪球](https://xueqiu.com/1915381653/376268419)
- **可信度**：★★★☆☆（二手整理）

**关于扎克伯格**：
Peter 提到扎克伯格和同事 Ned 整整一周都在玩他的产品，不断给反馈——"这个很棒"、"这个不行，得改"。

---

## 二、会议演讲与 Lightning Talks

### 2.1 Claude Code Anonymous — "Just One More Prompt"（2025年8月，伦敦）

- **来源**：[steipete.me](https://steipete.me/posts/2025/just-one-more-prompt)
- **可信度**：★★★★★（一手，有完整文字稿）

#### 核心即兴发言

**自我介绍的坦诚**：
> "Hi, my name is Peter and I'm a Claudoholic. I'm addicted to agentic engineering. And sometimes I just vibe-code."

**关于 AI 上瘾**：
> "AI was supposed to save time, yet I work more than ever before, I have more FOMO than ever before."（AI 本应节省时间，但我比以往工作更多，FOMO 也更严重。）

**关于"黑眼俱乐部"**：
他凌晨 4 点给朋友发短信，发现他们也都醒着。他管他们叫"Black Eye Club"。

**关于 VibeTunnel 的自嘲**：
他意识到自己构建了 VibeTunnel（一个把终端隧道到手机的工具），这样他就能更好地访问自己的"毒品"。

**关于工作节奏**：
> "I work in waves, a period of very intense work, followed by a period of slacking off."（我以波浪式工作——一段高强度工作，接着一段摸鱼。）

他不认为"常规"工作时间能做到这些，但承认已经到了不健康的程度。

**关于时间感知**：
他在 Claude 的状态栏加了会话时间显示，作为时间飞逝的提醒。

---

### 2.2 2026 年演讲日程

- **来源**：[GitHub steipete/speaking](https://github.com/steipete/speaking)
- **可信度**：★★★★★（一手）

他的演讲日程包括 TEDAI、CASE Conf 等会议。具体演讲内容待补充。

---

## 三、博客文章中的即兴思考与技术决策

### 3.1 "How We Work at PSPDFKit"（2019年7月）

- **来源**：[steipete.me](https://steipete.me/posts/2019/how-we-work)
- **可信度**：★★★★★（一手，详细技术博客）

#### 关于 SDK vs App 的本质差异
> "Developing an SDK has unique challenges… Since our SDK is integrated into thousands of apps, people expect our API to be consistent, and ideally it shouldn't ever change."

#### 关于代码寿命
> "Some code we ship was written in 2009, and it still works just as well today."

PSPDFKit 超过 100 万行代码，不能做"大重写"。

#### 关于 Proposal-Based Development
几乎每个功能都从提案开始，包含：Summary、Motivation、Details、Tradeoffs、所有平台的公共 API 设计、文档变更、开放问题、替代方案。提案作者负责推进流程。

#### 关于 Boy Scout Rule
> "We preach the Boy Scout Rule to 'leave it better than you found it,' and we do smaller cleanups with almost every PR."

#### 关于 Monorepo
像 Google 和 Facebook 一样，PSPDFKit 用一个巨大的 monorepo 管理几乎所有 SDK。

#### 关于 CI 的痛苦
> "Continuous Integration is really difficult to get right. We're constantly fighting with Apple's yearly OS updates, Xcode updates… and I haven't even mentioned flaky tests yet!"

macOS 的 CI 是最难管理的操作系统，因为"安全"功能如 Gatekeeper 无法通过 VNC 点击。

#### 关于 Experimental Fridays
工程师在"实验周五"创建了命令行工具来管理 changelog，因为 CHANGELOG.md 的合并冲突太频繁了。

---

### 3.2 "Claude Code is My Computer"（2025年6月）

- **来源**：[steipete.me](https://steipete.me/posts/2025/claude-code-is-my-computer)
- **可信度**：★★★★★（一手）

**核心观点**：
> "When I first installed Claude Code, I thought I was getting a smarter command line for coding tasks. What I actually got was a universal computer interface that happens to run in text."

**关于 --dangerously-skip-permissions**：
他用这个标志运行了两个月，零事故。用 Arq 小时级快照 + SuperDuper! 克隆做备份。

**关于 Warp 的局限**：
> "Warp… requires individual approval for each command — there's no equivalent to Claude's 'dangerous mode'… Also, Ghostty is just the better command line, native, not Electron-based and faster."

**关于开发者角色的转变**：
> "This isn't about AI replacing developers — it's about developers becoming orchestrators of incredibly powerful systems. The skill ceiling rises: syntax fades, system thinking shines."

---

### 3.3 "Finding My Spark Again"（2025年6月）

- **来源**：[steipete.me](https://steipete.me/posts/2025/finding-my-spark-again)
- **可信度**：★★★★★（一手，个人反思）

**关于卖公司后的空虚**：
> "I've been pouring 200% of my time, energy, and heart's blood into this company, and towards the end, I just felt that I needed a break."
>
> "For me though, I felt like I missed out on life."

**关于寻找意义**：
> "I did a lot of stuff, I partied hard, I did plenty of therapy, I did ayahuasca, I moved to another country, I wandered around carrying this emptiness in me and hunting hedonic pleasures."
>
> "I had enough of my own bullshit, and I realized that you don't find happiness by moving countries. You don't find purpose. **You create it.**"

**关于重新点燃激情**：
> "Creating things out of ideas, building was always the thing that gave me the most joy in life."

---

### 3.4 "My Current AI Dev Workflow"（2025年8月）

- **来源**：[steipete.me](https://steipete.me/posts/2025/optimal-ai-development-workflow)
- **可信度**：★★★★★（一手）

**工具选择的演变**：
> "After going all-in on VS Code, I went fully back to Ghostty… VS Code's terminal is too unstable, had plenty freezes when pasting in large amounts of text. Nothing beats Ghostty."

**关于 Gemini**：
> "Gemini can be great, but its edit tools are too messy, so using it less and less."

**关于 worktrees**：
> "I tried the whole worktree setup, just slows me down."

**关于 Claude 的"犯错与修复"**：
> "Claude often makes a mess but it's equally great in refactoring and cleaning up. Important to do both to not create too much technical debt."

**关于"Less is More"**：
> "Even removed my last MCP, since Claude sometimes would go off spinning up Playwright unasked when it could simply read the code."

**关于分布式系统设计**：
> "The hardest part is distributed system design, picking the right dependencies, platforms and a forward-thinking database schema."

**关于测试策略**：
> "Bigger changes always get tests. Automated ones usually aren't great, but the model almost always finds issues when you ask it to write tests IN THE SAME CONTEXT. Context is precious, don't waste it."

---

### 3.5 "Don't read this Startup Slop"（2025年8月）

- **来源**：[steipete.me](https://steipete.me/posts/2025/startup-slop)
- **可信度**：★★★★★（一手）

**关于被 Lobsters 封禁**：
他的网站因为用 AI 辅助写博客被 lobste.rs 封禁为"startup slop"。

**关于 slop 的定义**：
> "You can create slop with or without agents, as you can create great work with or without. Agents are just another tool."

**关于 AI 辅助写作 vs 自动化回复**：
> "There's a difference tho between automated replies and using agents to assist writing. At what point does it matter if I spend 4 hours prompting an agent to craft my thoughts into a post vs writing it manually?"

**关于 Twitter 内容**：
> "My Twitter takes are 100% handcrafted, artisan typed words. I don't even use WisprFlow there so you get the rawest, most organic experience."

---

### 3.6 "Self-Hosting AI Models"（2025年7月）

- **来源**：[steipete.me](https://steipete.me/posts/2025/self-hosting-ai-models)
- **可信度**：★★★★★（一手，技术深度分析）

**关于自托管的真实成本**：
8x H200 集群 $15/小时，24/7 运行约 $11,000/月。结论：不值得——阿里的 API 更便宜更快。

**关于开源模型的差距**：
> "It's great to know that open-source models are a merely 6-12 month behind the best commercial ones."

**关于 Claude Code 的不可替代性**：
> "Claude Code is insofar hard to replace, as it's this genius blend of amazing model & tooling."

---

### 3.7 "The State of SwiftUI"（2020年9月）

- **来源**：[steipete.me](https://steipete.me/posts/2020/state-of-swiftui)
- **可信度**：★★★★★（一手，技术深度分析）

**对 SwiftUI 生产就绪性的判断**：
> "I personally wouldn't yet go all-in on SwiftUI for production apps, although the crash rate is likely manageable."

**关于 AttributeGraph 崩溃**：
> "Most SwiftUI crashes are a result of either a diffing issue in AttributeGraph, or a bug with one of the bindings to the platform controls."

他用 Instruments 分析了 Apple 的 Fruta 示例应用，发现 30% 的时间花在 retain/release 和 malloc 上。AppKit 的 auto layout 与 SwiftUI 的 graph 结合非常耗时。

**关于 Catalyst vs AppKit**：
> "If you need to deploy your app to the Mac, use Catalyst, which is a much more stable binding."

**关于开发者的乐观**：
> "If you're curious about SwiftUI, please don't let this dampen your enthusiasm. It's extremely fun to write, it's clearly the future at Apple."

---

### 3.8 "Swifty Objective-C" / "Even Swiftier Objective-C"（2016/2017）

- **来源**：[steipete.me](https://steipete.me/posts/2016/swifty-objective-c) / [2017版](https://steipete.me/posts/2017/even-swiftier-objective-c)
- **可信度**：★★★★★（一手）

这些文章展示了他对代码风格演进的持续关注——如何让 Objective-C 更像 Swift。这也是 PSPDFKit 渐进式重构哲学的体现。

---

## 四、Twitter/X 上的讨论模式

### 4.1 关于 AI 编程工具的频繁对比

- **来源**：[@steipete on X](https://x.com/steipete)
- **可信度**：★★★★★（一手）

他频繁在 Twitter 上分享 AI 工具对比：
- 对 Codex 的偏好：能做长时间运行的任务，不会频繁中断
- 对 Claude Code 的又爱又恨：编辑能力强但 rate limits 痛苦
- 对 GPT-5 的评价：review 计划比 Gemini 好，但作为 agent 不够好
- 对 Gemini 的评价：速度极快，适合大上下文调试，但编辑工具太乱
- 对 Cursor/GPT-5 的评价：太慢，不分享思考过程，难以引导

### 4.2 关于工作方式的坦率分享

他在 Twitter 上公开分享：
- 6600+ commits/月（2026年1月）
- 16 小时工作日
- $6000/月的 Anthropic 账单
- 凌晨 4 点还在工作

### 4.3 改变立场的瞬间

**从 VS Code 回到 Ghostty**：
他曾"all-in on VS Code"，但后来完全回到 Ghostty。原因是 VS Code 终端在粘贴大量文本时冻结。

**从 MCP 到无 MCP**：
他移除了最后一个 MCP server，因为 Claude 有时会自作主张启动 Playwright。

**从 worktrees 到多份 checkout**：
他尝试了 worktree 工作流，认为增加了不必要的复杂性。改用 `clawbot-1` 到 `clawbot-5` 的多份 checkout。

---

## 五、对"好代码"与"坏代码"的态度

### 5.1 好代码的标准

**可维护性优先**：
> "Our biggest concerns have always been maintainability and long-term code evolution."

**API 一致性**：
> "People expect our API to be consistent, and ideally it shouldn't ever change."

**渐进式改进**：
> "We preach the Boy Scout Rule to 'leave it better than you found it.'"

**让 agent 能理解**：
> "I'm building a code base that is very easy for an agent to navigate."

### 5.2 坏代码的特征

**复杂编排系统**：
他把复杂的多 agent 编排系统称为"Slop Town"和"终极 Token 燃烧机"。

**24 小时无人监督的 agent 输出**：
> "你让它跑一整晚，第二天早上得到的是终极垃圾。"

**没有品味参与的代码**：
> "这些智能体还没有品味……如果你不引导它们，出来的就是垃圾。"

**追求完美主义而不动手**：
他认为过度追求完美的代码风格是一种误区。

### 5.3 对技术债务的态度

> "Claude often makes a mess but it's equally great in refactoring and cleaning up. Important to do both to not create too much technical debt."

他接受 agent 会产生混乱，但强调必须同时做重构和清理。

---

## 六、项目管理与工作方式

### 6.1 PSPDFKit 时期（2011-2021）

- **Proposal-based development**：每个功能从跨平台提案开始
- **Release train**：8 周一个 minor release，2 周一个 patch
- **Monorepo**：一个大仓库管理所有平台
- **Boy Scout Rule**：每个 PR 做小清理
- **Release Bot**：从 Slack 触发发布
- **productboard**：统一收集客户需求

### 6.2 OpenClaw 时期（2024-至今）

- **Discord 驱动开发**：扫描 help 频道，AI 总结痛点
- **一个人 + AI 军团**：6600+ commits/月
- **Prompt request 代替 PR**：关注意图而非代码
- **本地 CI**：不等远程 CI
- **多实例并行**：5 份 checkout 同时工作
- **人在循环**：品味和判断不可自动化

---

## 七、关键比喻与类比

| 比喻 | 语境 | 来源 |
|------|------|------|
| "Slop Town"（垃圾镇） | 复杂编排系统 | Peter Yang 访谈 |
| "Token 燃烧机" | 24 小时 agent 循环 | Peter Yang 访谈 |
| "虚荣指标" | 跑 agent 24 小时 | Peter Yang 访谈 |
| "黑眼俱乐部" | 凌晨 4 点还在工作的朋友们 | Claude Code Anonymous |
| "老虎机上瘾" | AI 编程的上瘾性 | Claude Code Anonymous |
| "住在你电脑里的怪朋友" | OpenClaw | Peter Yang 访谈 |
| "解除了枷锁的 ChatGPT" | 有电脑权限的 AI | Peter Yang 访谈 |
| "织毛衣" | 编程的未来 | Lex Fridman |
| "工厂" | 多实例并行工作 | Pragmatic Engineer |
| "Plan mode 是拼凑方案" | Anthropic 的 plan mode | Peter Yang 访谈 |

---

## 八、回避或拒绝回答的问题

1. **关于 OpenClaw 的商业计划**：他反复强调这是"hobby project"，对融资和商业模式问题轻描淡写。
2. **关于被收购**：虽然透露了 Meta 和 OpenAI 都来接触，但对具体细节和决策过程有所保留。
3. **关于 burnout 的深层原因**：在 Lex Fridman 访谈中提到 burnout 不只是编程，还包括人际关系，但没有展开。
4. **关于 ayahuasca 的体验**：只是一笔带过，没有详细描述。

---

## 九、信息来源汇总

| # | 来源 | 类型 | 可信度 | URL |
|---|------|------|--------|-----|
| 1 | The Pragmatic Engineer Podcast | 一手访谈 | ★★★★★ | https://newsletter.pragmaticengineer.com/p/the-creator-of-clawd-i-ship-code |
| 2 | Lex Fridman Podcast #491 | 一手访谈 | ★★★★★ | https://lexfridman.com/peter-steinberger/ |
| 3 | Peter Yang 访谈 | 一手访谈 | ★★★★☆ | https://baoyu.io/blog/2026/02/01/peter-steinberger-interview |
| 4 | Claude Code Anonymous 演讲 | 一手演讲 | ★★★★★ | https://steipete.me/posts/2025/just-one-more-prompt |
| 5 | steipete.me 博客（30+ 篇） | 一手博客 | ★★★★★ | https://steipete.me/posts |
| 6 | @steipete on X/Twitter | 一手社交 | ★★★★★ | https://x.com/steipete |
| 7 | GitHub steipete/speaking | 一手 | ★★★★★ | https://github.com/steipete/speaking |
| 8 | 雪球 Lex Fridman 细节整理 | 二手 | ★★★☆☆ | https://xueqiu.com/1915381653/376268419 |
| 9 | 宝玉 AI 翻译整理 | 二手翻译 | ★★★★☆ | https://baoyu.io/blog/2026/02/01/peter-steinberger-interview |
| 10 | SegmentFault/搜狐等转载 | 二手 | ★★★☆☆ | 多个转载源 |

---

## 十、未找到/待补充

- [ ] 他在 try! objc、NSSpain、Pragma Conference 的具体演讲视频和内容
- [ ] 他在 WWDC labs 的具体经历和对话
- [ ] 他在 Twitter/X 上的长线程讨论（需要直接搜索 X）
- [ ] 他在 Hacker News 上的评论（用户名可能为 steipete）
- [ ] 他对 Objective-C runtime 的深度技术讨论
- [ ] 他关于 Aspects/InterposeKit 的技术演讲
