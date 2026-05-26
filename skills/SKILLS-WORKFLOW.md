# Skills 协作工作流指南

32 个技能按场景组合使用，效益最大化。

---

## 🎯 触发词索引

用户说的关键词 → 应该命中哪个技能。Agent 收到用户输入后，先扫这张表。

| 触发词（中/英） | 技能 | 说明 |
|----------------|------|------|
| 需求分析、澄清需求、我想做、帮我设计、这个功能怎么做、spec、requirements、what should I build、按规范开发、规范点做 | `brainstorming` | 入口，先问清楚再动手 |
| 全局视角、这个模块是干嘛的、整体架构、帮我理一下、context、zoom out、higher level、big picture | `zoom-out` | 不熟悉代码时用 |
| 质疑方案、压力测试、grill me、审一下、挑毛病、找漏洞、stress test、challenge my plan | `grill-me` | 纯质询 |
| 同上 + 更新文档、同步到 CONTEXT.md、记录决策、ADR | `grill-with-docs` | 质询 + 自动更新文档 |
| 写计划、实施方案、拆任务、task breakdown、implementation plan、write a plan | `writing-plans` | 写详细实施计划 |
| 执行计划、开始开发、按计划做、execute the plan、implement this | `subagent-driven-development` / `executing-plans` | 按计划执行 |
| 并行处理、同时做、多任务、parallel、dispatch、at the same time、concurrently | `dispatching-parallel-agents` | 多个独立任务并行 |
| 代码审查、review、帮我看看代码、code review、PR 审查 | `requesting-code-review` | 请求审查 |
| 审查反馈、review comments、有人说、改一下这个、address feedback | `receiving-code-review` | 处理审查意见 |
| 验证一下、真的好了吗、跑一下测试、verify、prove it works、run tests | `verification-before-completion` | 完成前必须验证 |
| 收尾、合并、提交 PR、merge、创建分支、cleanup、finish up、wrap up | `finishing-a-development-branch` | 分支收尾 |
| 报 bug、出错了、不工作、broken、error、test fails、unexpected behavior、挂了、崩了、有问题、错了、看下这个问题、不对吧、重新看下、为什么、why、what's wrong、仔细查看、认真看、一行行看、逐行检查、仔细检查 | `systematic-debugging` | 先找根因 |
| 难复现、偶发、性能问题、hard bug、sporadic、flaky、regression、性能退化、为什么出这个问题、为什么不行、根因 | `diagnose` | 硬 bug 深度诊断 |
| 仔细查看、认真看、一行行看、逐行检查、仔细检查、review carefully、line by line、double check | `verification-before-completion` | 逐行验证 |
| TDD、测试驱动、先写测试、red-green-refactor、test first、写单测 | `tdd` / `test-driven-development` | 先写测试再写代码 |
| 重构、代码太乱、refactor、架构优化、解耦、模块化、可测试性 | `improve-codebase-architecture` | 架构分析 |
| 交接、换 session、handoff、上下文太长、继续之前的工作 | `handoff` | 会话交接 |
| 创建技能、写 skill、new skill、自定义技能 | `writing-skills` | 创建新技能 |
| React 性能、优化渲染、re-render、bundle size、瀑布请求、waterfall | `react-best-practices` | React 性能规则 |
| 组件设计、compound component、prop 太多、boolean props、组合模式 | `composition-patterns` | React 组合模式 |
| 审查 UI、无障碍、accessibility、a11y、UX 审查、check my UI、设计规范 | `web-design-guidelines` | Web UI 合规审查 |
| 页面动画、过渡效果、view transition、route animation、shared element、页面切换 | `react-view-transitions` | View Transition API |
| Vercel 优化、部署成本、函数调用量、CDN、vercel bill、slow routes | `vercel-optimize` | Vercel 部署审计 |
| 设计系统、UI 设计、交互设计、token、配色、排版、design system、mockup | `ui-ux-pro-max` | UI/UX 设计 |
| 去 AI 味、写得自然点、humanize、不像人写的、AI 痕迹、改写 | `humanizer` | 去除 AI 写作痕迹 |
| 学到了、记一下、教训、下次注意、lesson learned、mistake、搞错了 | `self-improving` / `self-improving-agent` | 自我改进 |
| 安装技能、新 skill、审查技能安全、install skill、vet skill | `skill-vetter` | 安装前安全审查 |
| GitHub、PR、Issue、CI、merge、gh CLI、workflow run | `github` | GitHub 操作 |
| 简单点写、不要过度设计、太复杂了、太臃肿、别加没要求的、写太多了、太长了、过度封装、别过度封装、过度防御、不可能的场景、代码太多、能精简吗、别处理不可能的、加个功能、冗余、有没可优化的、不要乱改、别动其他的、没坏别修、别改格式、保持原样、保持原有风格、别顺手改、不要改其他的、只改这个、最小改动、改代码、修代码、重构下、优化下、surgical edit、先想清楚、别猜、别假设、不确定、搞不懂、有歧义、有没有更简单的、想清楚了吗、搞明白了吗、先搞清楚、搞明白再写、没想清楚、不明确、为什么不问、不对、搞清楚、确定吗、有没更好的、karpathy、surgical、精准改动、改动要有依据、fix bug、fix it、错误信息、核对下、检查下、逐行、认真、仔细、怎么验证、成功标准、验收标准、怎么算完成、目标是什么、先写测试、写测试复现、先说计划、搞好就行、符合预期吗、达到预期了吗、验证了吗 | `karpathy-guidelines` | 编码行为约束：最简优先、精准改动、目标驱动 |

---

## ⚡ 快速决策表

遇到选择时，按此表判断：

| 场景 | 选 A | 选 B | 判断依据 |
|------|------|------|---------|
| 方案验证 | `grill-me` | `grill-with-docs` | 需要更新项目文档？→ grill-with-docs；纯验证 → grill-me |
| TDD | `tdd` | `test-driven-development` | 需要详细示例和反模式说明？→ tdd；快速上手 → test-driven-development |
| 执行计划 | `executing-plans` | `subagent-driven-development` | 有子代理支持？→ subagent-driven-development；没有 → executing-plans |
| 并行任务 | `subagent-driven-development` | `dispatching-parallel-agents` | 已有计划的系统性任务 → 前者；临时发现的独立任务 → 后者 |
| 硬 bug | `systematic-debugging` | `diagnose` | 一般 bug → systematic-debugging；难复现/性能问题 → diagnose |
| 仔细检查/逐行 | `karpathy-guidelines` + `verification-before-completion` | `systematic-debugging` | 有报错/异常？→ systematic-debugging；正常验证/写代码？→ karpathy + verification 叠加 |

---

## 🔨 1. 新功能开发（完整链路）

```
brainstorming（需求澄清，分段展示验证）  ← 入口门控，拿到需求先做这个
  → zoom-out（理解上下文）
  → grill-me / grill-with-docs（压力测试方案）
  → writing-plans（写实施计划）
  → subagent-driven-development / executing-plans（执行，叠加 karpathy-guidelines）
    → dispatching-parallel-agents（多任务并行分发）
  → requesting-code-review（审查，叠加 karpathy-guidelines）
  → receiving-code-review（处理审查反馈）
  → verification-before-completion（验证后再提交）
  → finishing-a-development-branch（合并/PR/清理）  ← 出口收尾
```

**要点**：
- `brainstorming` 是第一步，不要跳过。拿到需求先澄清，不要急着写代码。
- `grill-me` 和 `grill-with-docs` 二选一（见决策表）。
- `subagent-driven-development` 和 `executing-plans` 二选一（见决策表）。
- `finishing-a-development-branch` 是最后一步：验证测试 → 选择合并策略 → 清理分支。
- 写代码和审查代码时自动叠加 `karpathy-guidelines`：先想再写、最简优先、精准改动。

---

## 🐛 2. 修 Bug（定位→验证→收尾）

```
systematic-debugging（先找根因，禁止直接修）
  → diagnose（硬 bug 深度诊断：复现→最小化→假设→插桩→修复→回归测试）
  → tdd / test-driven-development（先写失败测试再修，karpathy Goal-Driven：定义成功标准）
  → verification-before-completion（验证通过才算完）
  → finishing-a-development-branch（收尾）
```

**要点**：
- `systematic-debugging` 强制"先找根因再修"；`diagnose` 是它的加强版，适合难复现的 bug。
- `tdd` 和 `test-driven-development` 二选一（见决策表）。
- 修 bug 前先写复现测试（karpathy Goal-Driven）：写测试复现 → 让测试通过 → 确认符合预期。

---

## 🔧 3. 重构

```
improve-codebase-architecture（发现架构问题、找"浅模块"变"深"的机会）
  → zoom-out（确认改动影响范围）
  → writing-plans（写重构计划）
  → executing-plans / subagent-driven-development（执行，叠加 karpathy-guidelines）
  → tdd（重构过程中用测试保护行为不变）
  → requesting-code-review（审查重构质量，叠加 karpathy-guidelines）
  → verification-before-completion
  → finishing-a-development-branch
```

**要点**：`improve-codebase-architecture` 会用"删除测试"判断模块价值，找出值得重构的 seam。

---

## ⚛️ 4. 写 React（自动叠加五件套）

```
brainstorming（需求澄清）  ← 入口
  → react-best-practices（性能规则，70 条）
  + composition-patterns（组合模式：compound components、render props）
  + web-design-guidelines（UI 审查：无障碍、UX 最佳实践）
  + ui-ux-pro-max（设计系统 token、组件规格、交互细节）
  + react-view-transitions（View Transition API 动画：页面切换、共享元素过渡）
```

**要点**：五个技能**同时参考**，不是串联。`react-best-practices` 管性能，`composition-patterns` 管架构，`web-design-guidelines` 管 UX 合规，`ui-ux-pro-max` 管设计质量，`react-view-transitions` 管动画过渡。

---

## 🎨 5. 纯 UI/UX 设计

```
brainstorming（需求澄清）
  → ui-ux-pro-max（设计方向、token 体系、组件规格）
  → web-design-guidelines（审查合规性）
  → composition-patterns（React 组件架构落地）
```

---

## 🚀 6. 长会话结束 / 切换上下文

```
handoff（压缩当前对话为交接文档，保存到临时目录，含"建议技能"段落）
```

**要点**：`handoff` 不保存到工作区，而是存到 OS 临时目录。适合跨 session 传递上下文。

---

## 📐 7. 多任务并行（效率倍增器）

```
dispatching-parallel-agents（多个独立任务 → 每个派一个子代理并行跑）
  + subagent-driven-development（有计划的多任务 → 每任务一个子代理 + 两轮审查）
```

**区别**：`dispatching-parallel-agents` 用于临时发现的并行任务（如多个独立 bug）；`subagent-driven-development` 用于已有计划的系统性开发。

---

## 🧠 8. 持续改进（贯穿始终）

```
self-improving（出错/被纠正/发现更好方案时自动触发，记忆存在 ~/self-improving/）
  + self-improving-agent（学习记录存在项目 .learnings/ 目录）
  + humanizer（去除 AI 写作痕迹，文档/PR 描述/提交信息都用）
  + skill-vetter（安装新技能前必做安全审查）
  + writing-skills（创建新技能时遵循最佳实践）
  + karpathy-guidelines（写代码/审查/重构时自动叠加：先想再写、最简优先、精准改动）
```

---

## 🔑 9. GitHub 操作

```
github（gh CLI：PR/Issue/CI/Run 操作，贯穿所有需要 git 协作的场景）
```

---

## ☁️ 10. Vercel 部署优化

```
vercel-optimize（Vercel 项目成本/性能/缓存/函数用量审计，生成排名报告）
```

---

## 一句话总结

`using-superpowers` 是元技能（告诉你怎么找技能），其余 31 个按场景组合：

- **新功能**：brainstorming → zoom-out → grill → plan → execute → review → verify → finish
- **修 bug**：systematic-debugging → diagnose → tdd（先写复现测试，定义成功标准）→ verify → finish
- **重构**：improve-codebase-architecture → zoom-out → plan → execute → review → verify → finish
- **写 React**：brainstorming → 五件套同时叠（react-best-practices + composition-patterns + web-design-guidelines + ui-ux-pro-max + react-view-transitions）
- **UI/UX 设计**：brainstorming → ui-ux-pro-max → web-design-guidelines
- **Vercel 优化**：vercel-optimize
- **结束**：handoff
- **全程**：self-improving + karpathy-guidelines 兜底

---

## 技能清单（32个）

### 核心技能（日常开发必用，15个）

| 技能 | 来源 | 场景 |
|------|------|------|
| brainstorming | superpowers | 需求澄清、设计讨论（入口） |
| zoom-out | mattpocock | 理解上下文、高层视角 |
| grill-me | mattpocock | 方案压力测试（纯质询） |
| writing-plans | superpowers | 写实施计划 |
| subagent-driven-development | superpowers | 子代理驱动开发 |
| requesting-code-review | superpowers | 请求代码审查 |
| verification-before-completion | superpowers | 完成前验证 |
| finishing-a-development-branch | superpowers | 分支收尾：合并/PR/清理 |
| systematic-debugging | superpowers | 系统化调试 |
| tdd | mattpocock | 测试驱动开发 |
| handoff | mattpocock | 会话交接 |
| self-improving | clawhub | 自我反思与改进 |
| humanizer | clawhub | 去除 AI 写作痕迹 |
| github | clawhub | GitHub 操作 |
| karpathy-guidelines | clawhub | 编码行为约束：最简优先、精准改动、目标驱动（全程生效） |

### React 专用（写 React 时叠加，5个）

| 技能 | 来源 | 场景 |
|------|------|------|
| react-best-practices | vercel | React 性能优化（70 条规则） |
| composition-patterns | vercel | 组合模式、避免 prop 膨胀 |
| web-design-guidelines | vercel | Web UI 审查、无障碍 |
| react-view-transitions | vercel | View Transition API 动画 |
| ui-ux-pro-max | clawhub | 设计系统 token、组件规格 |

### 按需选用（特定场景，11个）

| 技能 | 来源 | 场景 |
|------|------|------|
| grill-with-docs | mattpocock | 方案压力测试 + 自动更新文档 |
| diagnose | mattpocock | 硬 bug 深度诊断 |
| improve-codebase-architecture | mattpocock | 架构分析、重构机会发现 |
| executing-plans | superpowers | 执行计划（无子代理时用） |
| dispatching-parallel-agents | superpowers | 并行任务分发 |
| receiving-code-review | superpowers | 处理审查反馈 |
| test-driven-development | superpowers | TDD 简洁版 |
| writing-skills | superpowers | 创建新技能规范 |
| vercel-optimize | vercel | Vercel 部署优化审计 |
| self-improving-agent | clawhub | 学习记录 |
| skill-vetter | clawhub | 技能安全审查 |

### 元技能（1个）

| 技能 | 来源 | 场景 |
|------|------|------|
| using-superpowers | superpowers | 怎么找技能、技能系统入门 |
