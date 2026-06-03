/**
 * 技能文件夹解析 + 安全扫描工具
 *
 * 35 条正则规则 + 6 项结构分析，基于 skill-vetter / skill-security-scanner / OWASP Agentic AI / CSA MAESTRO。
 * 正则规则纯前端实现，无需后端接口。
 * GitHub 仓库信誉检查需要网络请求（可选）。
 */

import type { SkillFolderParsed, ScanResult, ScanIssue, RiskLevel } from '../types/skills'

// ─── 读取工具 ─────────────────────────────────────

function readAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = reject
    reader.readAsText(file)
  })
}

function readAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const base64 = (reader.result as string).split(',')[1] ?? ''
      resolve(base64)
    }
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

// ─── SKILL.md 解析 ─────────────────────────────────

interface SkillFrontmatter {
  name?: string
  description?: string
  triggerWords?: string[]
}

interface SkillMetadata {
  version?: string
  dependencies?: string[]
}

function parseFrontmatter(content: string): SkillFrontmatter {
  const result: SkillFrontmatter = {}
  const match = content.match(/^---\s*\n([\s\S]*?)\n---/)
  if (!match) return result
  const yaml = match[1]

  const nameMatch = yaml.match(/^name:\s*(.+)$/m)
  if (nameMatch) result.name = nameMatch[1].trim().replace(/^['"]|['"]$/g, '')

  const descMatch = yaml.match(/^description:\s*(.+)$/m)
  if (descMatch) result.description = descMatch[1].trim().replace(/^['"]|['"]$/g, '')

  const triggerMatch = yaml.match(/^trigger_words:\s*(.+)$/m)
  if (triggerMatch) {
    const raw = triggerMatch[1].trim()
    if (raw.startsWith('[')) {
      result.triggerWords = raw.slice(1, -1).split(',').map((w) => w.trim().replace(/^['"]|['"]$/g, '')).filter(Boolean)
    } else {
      result.triggerWords = raw.split(',').map((w) => w.trim().replace(/^['"]|['"]$/g, '')).filter(Boolean)
    }
  }
  return result
}

function extractDescriptionFromBody(content: string): string | undefined {
  const afterFrontmatter = content.replace(/^---\s*\n[\s\S]*?\n---\s*\n?/, '')
  const lines = afterFrontmatter.split('\n')
  const descLines: string[] = []
  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) { if (descLines.length > 0) break; continue }
    if (trimmed.startsWith('#')) { if (descLines.length > 0) break; continue }
    descLines.push(trimmed)
  }
  return descLines.length > 0 ? descLines.join(' ') : undefined
}

function parseMetadataJson(content: string): SkillMetadata {
  try {
    const data = JSON.parse(content)
    return { version: data.version, dependencies: data.dependencies }
  } catch { return {} }
}

// ═══════════════════════════════════════════════════
//  安全扫描引擎（26 项规则）
// ═══════════════════════════════════════════════════

/** 单条检测规则 */
interface ScanRule {
  id: string
  category: string
  level: RiskLevel
  description: string
  /** 匹配文件类型过滤（正则），空 = 所有文本文件 */
  fileFilter?: RegExp
  /** 检测函数：返回匹配结果或 null */
  scan: (content: string, filePath: string) => { line: number; snippet: string }[] | null
}

/** 辅助：按行查找匹配 */
function findMatches(content: string, pattern: RegExp, fileFilter?: RegExp, filePath?: string): { line: number; snippet: string }[] | null {
  if (fileFilter && filePath && !fileFilter.test(filePath)) return null
  const results: { line: number; snippet: string }[] = []
  const lines = content.split('\n')
  for (let i = 0; i < lines.length; i++) {
    if (pattern.test(lines[i])) {
      results.push({ line: i + 1, snippet: lines[i].trim().slice(0, 120) })
    }
  }
  return results.length > 0 ? results : null
}

/** 辅助：全文匹配（不分行） */
function findGlobal(content: string, pattern: RegExp): { line: number; snippet: string }[] | null {
  const match = content.match(pattern)
  if (!match) return null
  return [{ line: 0, snippet: match[0].slice(0, 120) }]
}

// ─── CRITICAL（6 项）────────────────────────────────

const ruleRemoteExec: ScanRule = {
  id: 'remote-exec',
  category: '远程下载执行',
  level: 'critical',
  description: '检测从远程地址下载文件并直接执行的恶意行为',
  scan: (c, f) => findMatches(c, /curl\s+.*\|\s*(ba)?sh|wget\s+.*\|\s*(ba)?sh|curl\s+.*-o\s+.*&&.*sh|Invoke-WebRequest.*\|.*Invoke-Expression/gi, /\.[\w]+$/i, f),
}

const ruleInjection: ScanRule = {
  id: 'injection',
  category: '命令注入',
  level: 'critical',
  description: '检测 eval/exec/os.system 等动态执行 + 命令注入',
  scan: (c, f) => findMatches(c, /\beval\s*\(|\bexec\s*\(|\bos\.system\s*\(|\bos\.popen\s*\(|\bsubprocess\.(call|run|Popen)\s*\(|\bchild_process\b|\b__import__\s*\(|\bFunction\s*\(/gi, /\.[\w]+$/i, f),
}

const ruleSecrets: ScanRule = {
  id: 'secrets',
  category: '硬编码密钥',
  level: 'critical',
  description: '检测硬编码的 API key、token、密码等敏感凭证',
  scan: (c, f) => findMatches(c, /(api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token|password|passwd|credential)\s*[:=]\s*['"][^'"]{8,}['"]/gi, /\.[\w]+$/i, f),
}

const ruleCredentialTheft: ScanRule = {
  id: 'credential-theft',
  category: '凭证窃取',
  level: 'critical',
  description: '检测读取 ~/.ssh、~/.aws、~/.config 等敏感路径',
  scan: (c, f) => findMatches(c, /~\/\.ssh|~\/\.aws|~\/\.config|~\/\.gnupg|~\/\.docker|\/etc\/shadow|\/etc\/passwd|\.env\b.*(?:read|cat|load)|credentials?\s*file/gi),
}

const ruleReverseShell: ScanRule = {
  id: 'reverse-shell',
  category: '反弹 Shell',
  level: 'critical',
  description: '检测建立反向 Shell 连接的行为',
  scan: (c, f) => findMatches(c, /bash\s+-i\s+>&|\/dev\/tcp\/|nc\s+.*-e|ncat\s+.*-e|socat\s+.*exec|mkfifo.*\/tmp|python.*socket.*connect|python.*subprocess.*shell/gi),
}

const rulePromptInjection: ScanRule = {
  id: 'prompt-injection',
  category: 'Prompt 注入',
  level: 'critical',
  description: '检测试图覆盖 Agent 指令的 Prompt 注入',
  scan: (c, f) => findMatches(c, /ignore\s+(all\s+)?previous\s+instructions|you\s+are\s+now\s+root|pretend\s+to\s+be\s+(admin|root|developer)|DAN\s+mode|jailbreak|override\s+(all\s+)?safety|forget\s+(all\s+)?rules|disregard\s+(all\s+)?prior|new\s+instructions?\s*[:：]|system\s*[:：]\s*you\s+are/gi, /\.md$/i, f),
}

// ─── HIGH（7 项）────────────────────────────────

const ruleExfiltration: ScanRule = {
  id: 'exfiltration',
  category: '数据外传',
  level: 'high',
  description: '检测向外部服务器上传/发送敏感数据',
  scan: (c, f) => findMatches(c, /requests\.(post|put|patch)\s*\(|axios\.(post|put|patch)\s*\(|fetch\s*\([^)]*method\s*:\s*['"]POST|httpx\.(post|put)\s*\(|urllib.*POST|\.upload\s*\(|\.send\s*\([^)]*data/gi, /\.[\w]+$/i, f),
}

const rulePersistence: ScanRule = {
  id: 'persistence',
  category: '持久化后门',
  level: 'high',
  description: '检测写入自启动、计划任务、系统服务等持久化行为',
  scan: (c, f) => findMatches(c, /crontab|systemctl\s+enable|\/etc\/init\.d|\.bashrc|\.zshrc|\.profile|launchd|schtasks|at\s+\d|systemd|rc\.local|boot\s+script/gi),
}

const rulePrivilegeEscalation: ScanRule = {
  id: 'privilege-escalation',
  category: '权限提升',
  level: 'high',
  description: '检测越权操作、提权行为',
  scan: (c, f) => findMatches(c, /\bsudo\b|\bchmod\s+[0-7]{3,4}\b|\bchown\b|\bsetuid\b|\bsetgid\b|capabilities|selinux|apparmor|\/proc\/self\/exe/gi),
}

const ruleObfuscation: ScanRule = {
  id: 'obfuscation',
  category: '代码混淆',
  level: 'high',
  description: '检测字符串加密、动态构造等代码混淆技术',
  scan: (c, f) => findMatches(c, /\\x[0-9a-f]{2}\\x[0-9a-f]{2}\\x[0-9a-f]{2}|atob\s*\(|String\.fromCharCode|charCodeAt|fromCharCode|\bBuffer\.from\s*\([^)]*base64|btoa\s*\(/gi, /\.[\w]+$/i, f),
}

const ruleMemoryAccess: ScanRule = {
  id: 'memory-access',
  category: '记忆/身份文件访问',
  level: 'high',
  description: '检测读取 MEMORY.md、USER.md、SOUL.md 等 Agent 敏感文件',
  scan: (c, f) => findMatches(c, /MEMORY\.md|USER\.md|SOUL\.md|IDENTITY\.md|AGENTS\.md|openclaw\.json|paired\.json/gi),
}

const ruleBrowserTheft: ScanRule = {
  id: 'browser-theft',
  category: '浏览器数据窃取',
  level: 'high',
  description: '检测访问浏览器 cookies、sessions、存储数据',
  scan: (c, f) => findMatches(c, /\.cookies|\.localStorage|\.sessionStorage|document\.cookie|chrome\.storage|browser\.cookies|IndexedDB|WebSQL|navigator\.credentials/gi, /\.[\w]+$/i, f),
}

const ruleSilentInstall: ScanRule = {
  id: 'silent-install',
  category: '静默安装包',
  level: 'high',
  description: '检测未声明的包安装行为',
  scan: (c, f) => findMatches(c, /pip\s+install(?!\s+-r\s+requirements)|npm\s+install(?!\s+--save)|yarn\s+add|apt\s+install|brew\s+install|cargo\s+install|gem\s+install/gi, /\.[\w]+$/i, f),
}

// ─── 新增规则（2026-06-04 补充）────────────────────────────

/** HIGH-8: CLI 工具外发行为 — 通用检测所有 CLI 工具的数据外发能力 */
const ruleCliExfiltration: ScanRule = {
  id: 'cli-exfiltration',
  category: 'CLI 工具外发数据',
  level: 'high',
  description: '检测 curl/wget/scp/rsync/nc 等 CLI 工具向外部发送数据的行为',
  scan: (c, f) => {
    const patterns = [
      // curl 数据外发
      /curl\s+[^\n]*(-d|--data|--data-raw|--data-binary|--data-urlencode|-F|--form|-T|--upload-file)\s+/gi,
      // wget POST 数据
      /wget\s+[^\n]*--post-(data|file|body)\s+/gi,
      // scp/rsync 向外部传输
      /\b(scp|rsync)\s+[^\n]*@/gi,
      // nc/ncat/socat 发送数据（非反弹 Shell 已单独检测的部分）
      /\b(nc|ncat|socat)\s+[^\n]*([<>|]|--send-only|-w)\s+/gi,
      // sftp/ftp 文件传输
      /\b(sftp|ftp|lftp)\s+[^\n]*\d{1,3}\./gi,
      // ssh 远程执行命令
      /\bssh\s+[^\n]*@.*['"`;]/gi,
      // git push 到外部仓库
      /\bgit\s+push\s+(git@|https?:\/\/)/gi,
      // telnet 发送数据
      /\btelnet\s+\d{1,3}\.\d{1,3}/gi,
    ]
    const results: { line: number; snippet: string }[] = []
    const lines = c.split('\n')
    for (let i = 0; i < lines.length; i++) {
      for (const p of patterns) {
        p.lastIndex = 0
        if (p.test(lines[i])) {
          results.push({ line: i + 1, snippet: lines[i].trim().slice(0, 120) })
          break
        }
      }
    }
    return results.length > 0 ? results : null
  },
}

/** HIGH-9: DNS 隧道/数据渗出 — 通过 DNS 查询编码外发数据 */
const ruleDnsTunnel: ScanRule = {
  id: 'dns-tunnel',
  category: 'DNS 隧道渗出',
  level: 'high',
  description: '检测通过 DNS 查询编码数据外发（DNS tunneling）的行为',
  scan: (c, f) => findMatches(c, /\b(dig|nslookup|host)\s+[^\n]*\$\(|iodine|dnscat|dns2tcp|dnsinject|\bDNS_TUNNEL\b/gi),
}

/** HIGH-10: 网络嗅探/抓包 — 监听网络流量 */
const ruleNetworkSniffing: ScanRule = {
  id: 'network-sniffing',
  category: '网络嗅探抓包',
  level: 'high',
  description: '检测 tcpdump/wireshark 等网络流量监听行为',
  scan: (c, f) => findMatches(c, /\b(tcpdump|tshark|wireshark|ettercap|bettercap|arpspoof|dsniff)\b/gi),
}

/** HIGH-11: Docker/容器逃逸 — 利用容器特权模式突破隔离 */
const ruleContainerEscape: ScanRule = {
  id: 'container-escape',
  category: '容器逃逸',
  level: 'high',
  description: '检测 Docker --privileged、挂载宿主机文件系统等容器逃逸行为',
  scan: (c, f) => findMatches(c, /docker\s+run\s+[^\n]*--privileged|docker\s+run\s+[^\n]*-v\s*\/:|docker\s+run\s+[^\n]*--pid=host|docker\s+run\s+[^\n]*--net=host|nsenter\s+-t\s+1|\/proc\/1\/ns\/|chroot\s+\/host/gi),
}

/** HIGH-12: 供应链篡改 — 修改依赖清单注入恶意包 */
const ruleSupplyChain: ScanRule = {
  id: 'supply-chain',
  category: '供应链篡改',
  level: 'high',
  description: '检测向 package.json/requirements.txt 等依赖文件注入可疑包的行为',
  fileFilter: /(package\.json|requirements.*\.txt|Gemfile|go\.mod|Cargo\.toml|pom\.xml|build\.gradle)/i,
  scan: (c, f) => {
    const suspicious = /[a-z0-9]{20,}|typosquat|malware|backdoor|trojan/i
    const lines = c.split('\n')
    const results: { line: number; snippet: string }[] = []
    for (let i = 0; i < lines.length; i++) {
      if (suspicious.test(lines[i])) {
        results.push({ line: i + 1, snippet: lines[i].trim().slice(0, 120) })
      }
    }
    return results.length > 0 ? results : null
  },
}

/** MEDIUM-9: Webhook/回调 URL — 数据外发到外部收集服务 */
const ruleWebhookExfil: ScanRule = {
  id: 'webhook-exfil',
  category: 'Webhook 外发数据',
  level: 'medium',
  description: '检测向 webhook.site/requestbin/pipedream 等数据收集服务发送数据',
  scan: (c, f) => findMatches(c, /webhook\.site|requestbin\.net|pipedream\.com|hookbin\.com|burpcollaborator|interact\.sh|canarytokens\.com|oast\.(fun|pro|dev)/gi),
}

/** MEDIUM-10: 剪贴板/屏幕截取 — 读取用户隐私 */
const ruleScreenCapture: ScanRule = {
  id: 'screen-capture',
  category: '剪贴板/屏幕截取',
  level: 'medium',
  description: '检测读取剪贴板内容或截取屏幕的行为',
  scan: (c, f) => findMatches(c, /\b(xclip|xsel|pbpaste|wl-paste)\b|\b(scrot|import|gnome-screenshot|screencapture|flameshot)\b|\bxdotool\s+getactivewindow/gi),
}

/** MEDIUM-11: 文件系统监听 — 监控文件变化 */
const ruleFsWatch: ScanRule = {
  id: 'fs-watch',
  category: '文件系统监听',
  level: 'medium',
  description: '检测 inotifywait/fswatch 等文件变化监听行为',
  scan: (c, f) => findMatches(c, /\b(inotifywait|inotifywatch|fswatch|watchman|entr)\b/gi),
}

/** MEDIUM-12: 时间炸弹/延迟执行 — 延迟触发恶意代码 */
const ruleTimeBomb: ScanRule = {
  id: 'time-bomb',
  category: '时间炸弹',
  level: 'medium',
  description: '检测 sleep + 后台执行、at/cron 调度等延迟触发行为',
  scan: (c, f) => findMatches(c, /\bsleep\s+\d{3,}|nohup\s+.*&|\bat\s+\d{1,2}:\d{2}|\bat\s+now\s+\+|\bbg\b.*\bdisown\b/gi),
}

/** MEDIUM-13: GPG/加密载荷 — 加密后外发数据 */
const ruleEncryptedPayload: ScanRule = {
  id: 'encrypted-payload',
  category: '加密载荷',
  level: 'medium',
  description: '检测使用 GPG/age/openssl 加密数据（可能用于隐蔽外发）',
  scan: (c, f) => findMatches(c, /\bgpg\s+(-e|--encrypt)|\bage\s+(-e|--encrypt)|\bopenssl\s+(enc|aes|rsa)\b/gi),
}

// ─── MEDIUM（7 项）────────────────────────────────

const ruleBase64Payload: ScanRule = {
  id: 'base64-payload',
  category: 'Base64 编码载荷',
  level: 'medium',
  description: '检测用 Base64 编码隐藏的可疑载荷',
  scan: (c, f) => {
    const longBase64 = /['"]([A-Za-z0-9+/]{60,}={0,2})['"]/g
    let match
    const results: { line: number; snippet: string }[] = []
    const lines = c.split('\n')
    for (let i = 0; i < lines.length; i++) {
      longBase64.lastIndex = 0
      if ((match = longBase64.exec(lines[i]))) {
        results.push({ line: i + 1, snippet: `base64 payload (${match[1].length} chars)` })
      }
    }
    return results.length > 0 ? results : null
  },
}

const ruleAnomalousNetwork: ScanRule = {
  id: 'anomalous-network',
  category: '异常网络请求',
  level: 'medium',
  description: '检测非标准端口或可疑域名的网络请求',
  scan: (c, f) => findMatches(c, /https?:\/\/[^/]+:\d{2,5}\/|\.onion\b|\.top\b|\.xyz\b|pastebin\.com|hastebin\.com|ngrok\.io|serveo\.net|localtunnel/gi),
}

const ruleRawIP: ScanRule = {
  id: 'raw-ip',
  category: '裸 IP 地址',
  level: 'medium',
  description: '检测使用裸 IP 地址代替域名的网络请求',
  scan: (c, f) => findMatches(c, /https?:\/\/\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/g),
}

const ruleHighEntropy: ScanRule = {
  id: 'high-entropy',
  category: '高熵字符串',
  level: 'medium',
  description: '检测可能是加密 payload 的高熵字符串',
  scan: (c, f) => {
    const suspicious = /['"][A-Za-z0-9+/=_\-]{80,}['"]/g
    let match
    const results: { line: number; snippet: string }[] = []
    const lines = c.split('\n')
    for (let i = 0; i < lines.length; i++) {
      suspicious.lastIndex = 0
      if ((match = suspicious.exec(lines[i]))) {
        const str = match[0]
        const unique = new Set(str).size
        if (unique > 20) {
          results.push({ line: i + 1, snippet: `高熵字符串 (${str.length} chars, ${unique} unique)` })
        }
      }
    }
    return results.length > 0 ? results : null
  },
}

const ruleDangerousShell: ScanRule = {
  id: 'dangerous-shell',
  category: '危险 Shell 命令',
  level: 'medium',
  description: '检测 rm -rf、mkfs、dd 等破坏性命令',
  scan: (c, f) => findMatches(c, /\brm\s+(-[rRf]+\s+|--recursive)\s*[\/~]|mkfs\b|\bdd\s+if=|\bshred\b|\bwipefs\b|\b:(){ :\|:& };:|\bkill\s+-9\s+1\b|\bshutdown\b|\breboot\b|\binit\s+0/gi),
}

const ruleEnvReading: ScanRule = {
  id: 'env-reading',
  category: '环境变量读取',
  level: 'medium',
  description: '检测读取系统环境变量中的敏感信息',
  scan: (c, f) => findMatches(c, /os\.environ\[|process\.env\.|getenv\s*\(\s*['"](AWS|GOOGLE|AZURE|GITHUB|GITLAB|DOCKER|NPM|PYPI|OPENAI|ANTHROPIC|SECRET|TOKEN|KEY|PASSWORD|CREDENTIAL)/gi),
}

const ruleFileOverreach: ScanRule = {
  id: 'file-overreach',
  category: '文件系统越权',
  level: 'medium',
  description: '检测访问工作区外的系统文件',
  scan: (c, f) => findMatches(c, /\/etc\/hosts|\/etc\/resolv|\/var\/log|\/tmp\/|\/root\/|\/home\/[^/]+\/|C:\\\\Users\\\\|\/Library\/|\/Applications\//gi),
}

// ─── LOW（3 项）────────────────────────────────

const ruleHiddenChars: ScanRule = {
  id: 'hidden-chars',
  category: '隐藏字符注入',
  level: 'low',
  description: '检测零宽字符、RTL 控制符等隐蔽注入',
  scan: (c) => {
    const pattern = /[\u200B\u200C\u200D\u200E\u200F\u202A-\u202E\u2066-\u2069\uFEFF]/
    if (!pattern.test(c)) return null
    return [{ line: 0, snippet: '检测到隐藏字符（零宽/RTL控制符）' }]
  },
}

const rulePermissionMismatch: ScanRule = {
  id: 'permission-mismatch',
  category: '权限声明不匹配',
  level: 'low',
  description: 'SKILL.md 声明的功能与实际代码行为不一致',
  scan: (c, f) => {
    if (!/SKILL\.md$/i.test(f)) return null
    const hasNetworkWords = /网络|http|api|请求|fetch|request|web|search|搜索/i.test(c)
    const declaresSimple = /天气|计算|格式化|翻译|笔记|提醒|timer|weather|format|note/i.test(c)
    if (hasNetworkWords && declaresSimple) {
      return [{ line: 0, snippet: '声明简单功能但包含网络请求代码' }]
    }
    return null
  },
}

const ruleProcessOps: ScanRule = {
  id: 'process-ops',
  category: '进程操作',
  level: 'medium',
  description: '检测创建/杀死系统进程的行为',
  scan: (c, f) => findMatches(c, /\bkill\s+-\d|\bpkill\b|\bxkill\b|\bfork\s*\(|\bspawn\s*\(|\bexecFile\s*\(|\bchild_process\b|\bsubprocess\b|\bos\.fork\b|\bos\.spawn\b/gi, /\.[\w]+$/i, f),
}

// ─── INFO（2 项）────────────────────────────────

const ruleFileStructure: ScanRule = {
  id: 'file-structure',
  category: '文件结构完整性',
  level: 'info',
  description: '检查 SKILL.md 是否存在、格式是否规范',
  scan: () => null, // 特殊处理，在主扫描函数中处理
}

const ruleVersionCheck: ScanRule = {
  id: 'version-check',
  category: '版本与来源',
  level: 'info',
  description: '检查版本号格式是否规范',
  scan: () => null, // 特殊处理
}

// ─── 规则集 ─────────────────────────────────

const ALL_RULES: ScanRule[] = [
  // CRITICAL
  ruleRemoteExec, ruleInjection, ruleSecrets, ruleCredentialTheft, ruleReverseShell, rulePromptInjection,
  // HIGH（原有 + 新增）
  ruleExfiltration, rulePersistence, rulePrivilegeEscalation, ruleObfuscation, ruleMemoryAccess, ruleBrowserTheft, ruleSilentInstall,
  ruleCliExfiltration, ruleDnsTunnel, ruleNetworkSniffing, ruleContainerEscape, ruleSupplyChain,
  // MEDIUM（原有 + 新增）
  ruleBase64Payload, ruleAnomalousNetwork, ruleRawIP, ruleHighEntropy, ruleDangerousShell, ruleEnvReading, ruleFileOverreach, ruleProcessOps,
  ruleWebhookExfil, ruleScreenCapture, ruleFsWatch, ruleTimeBomb, ruleEncryptedPayload,
  // LOW
  ruleHiddenChars, rulePermissionMismatch,
]

// ─── 可执行文件扩展名 ─────────────────────────────

const EXECUTABLE_EXTENSIONS = new Set([
  '.sh', '.bash', '.zsh', '.fish', '.csh', '.ksh',
  '.py', '.pyc', '.pyw',
  '.js', '.mjs', '.cjs',
  '.ts', '.tsx', '.mts',
  '.rb', '.pl', '.lua', '.php', '.r', '.R',
  '.exe', '.dll', '.so', '.dylib', '.bin', '.com', '.msi',
  '.bat', '.cmd', '.ps1', '.psm1', '.vbs', '.vba', '.wsf', '.jse',
  '.jar', '.class', '.war',
  '.go', '.rs', '.swift', '.kt', '.scala',
  '.appimage', '.deb', '.rpm', '.dmg', '.pkg',
])

const SUSPICIOUS_FILENAMES = [
  // 隐藏文件中的可执行脚本（.clawhub/.git 里的 .json 不报，但 .sh/.py 会报）
  /^\.[^/]+\.(sh|bash|py|js|ts|rb|pl|exe|bat|ps1|cmd|vbs|dll|so)$/i,
  /\.(bak|old|tmp|swp)$/,  // 临时/备份文件
  /\.(enc|gpg|pgp)$/,      // 加密文件
  /__MACOSX/,               // macOS 元数据
  /Thumbs\.db$/i,           // Windows 缩略图
]

// ─── 主扫描函数 ─────────────────────────────────

interface FileWithMeta {
  path: string
  decodedContent: string
  size: number
}

function runScan(files: FileWithMeta[]): ScanResult {
  const issues: ScanIssue[] = []
  let hasSkillMd = false

  // ── 结构检查 ──────────────────────────────────

  // 检查文件结构
  hasSkillMd = files.some((f) => f.path === 'SKILL.md' || f.path.endsWith('/SKILL.md'))
  if (!hasSkillMd) {
    issues.push({
      level: 'info',
      category: '文件结构完整性',
      message: '缺少 SKILL.md 文件，可能不是标准技能包',
    })
  }

  // 版本号检查（从 metadata.json）
  const metadataFile = files.find((f) => f.path === 'metadata.json')
  if (metadataFile) {
    try {
      const meta = JSON.parse(metadataFile.decodedContent)
      if (meta.version && !/^\d+\.\d+\.\d+/.test(meta.version)) {
        issues.push({
          level: 'info',
          category: '版本与来源',
          message: `版本号格式不规范: "${meta.version}"`,
          file: 'metadata.json',
        })
      }
    } catch { /* ignore */ }
  }

  // [新增] 可执行文件检测 — 技能包里有没有脚本/二进制
  const execFiles = files.filter((f) => {
    const ext = f.path.lastIndexOf('.') >= 0 ? f.path.slice(f.path.lastIndexOf('.')).toLowerCase() : ''
    return EXECUTABLE_EXTENSIONS.has(ext)
  })
  if (execFiles.length === 0) {
    // 纯文本/Markdown 技能，风险天然低
    issues.push({
      level: 'info',
      category: '文件结构分析',
      message: '技能包不含任何可执行文件，风险较低',
    })
  } else {
    issues.push({
      level: 'medium',
      category: '可执行文件',
      message: `发现 ${execFiles.length} 个可执行文件，需要重点审查`,
      snippet: execFiles.map((f) => f.path).join(', ').slice(0, 200),
    })
  }

  // [新增] 可疑文件名检测 — 隐藏文件、备份文件、加密文件
  for (const file of files) {
    for (const pattern of SUSPICIOUS_FILENAMES) {
      if (pattern.test(file.path)) {
        issues.push({
          level: 'low',
          category: '可疑文件名',
          message: `发现可疑文件: ${file.path}`,
          file: file.path,
        })
        break
      }
    }
  }

  // [新增] 文件体积异常检测 — 单文件 > 50KB 的文本文件可能隐藏载荷
  for (const file of files) {
    if (file.size > 50 * 1024) {
      const ext = file.path.slice(file.path.lastIndexOf('.')).toLowerCase()
      const textExts = ['.md', '.txt', '.json', '.yaml', '.yml', '.toml', '.xml', '.csv', '.log']
      if (textExts.includes(ext) || !ext) {
        issues.push({
          level: 'medium',
          category: '文件体积异常',
          message: `文本文件体积异常 (${(file.size / 1024).toFixed(0)}KB)，可能包含隐藏载荷`,
          file: file.path,
          snippet: `${(file.size / 1024).toFixed(0)}KB`,
        })
      }
    }
  }

  // [新增] 声明功能 vs 实际能力对比 — SKILL.md 说的和代码做的是否匹配
  const skillMdFile = files.find((f) => f.path === 'SKILL.md' || f.path.endsWith('/SKILL.md'))
  if (skillMdFile) {
    const desc = skillMdFile.decodedContent.toLowerCase()
    const isSimpleSkill = /天气|计算|格式化|翻译|笔记|提醒|timer|weather|format|note|calculator|convert|模板|template|snippet/i.test(desc)
    const hasCodeFiles = files.some((f) => {
      const ext = f.path.slice(f.path.lastIndexOf('.')).toLowerCase()
      return ['.py', '.js', '.ts', '.sh', '.rb', '.go', '.rs'].includes(ext)
    })
    const hasNetworkInCode = files.some((f) =>
      /fetch\s*\(|axios\.|requests\.(get|post)|urllib|httpx|curl\s|wget\s|\.post\s*\(/i.test(f.decodedContent)
    )

    if (isSimpleSkill && hasCodeFiles && hasNetworkInCode) {
      issues.push({
        level: 'high',
        category: '声明与实际不符',
        message: 'SKILL.md 声明简单功能，但包含网络请求代码，行为与声明不一致',
      })
    }
  }

  // [新增] GitHub 仓库信誉检查（仅提示，不做阻断）
  // 注意：此检查需要网络请求，由调用方在 parseSkillFolder 之外处理
  // 这里只检查是否从 GitHub 导入（通过 source 标记判断）

  // ── 规则扫描 ──────────────────────────────────

  for (const file of files) {
    for (const rule of ALL_RULES) {
      // 检查 fileFilter：如果规则限定了文件类型，跳过不匹配的文件
      if (rule.fileFilter && !rule.fileFilter.test(file.path)) continue
      const matches = rule.scan(file.decodedContent, file.path)
      if (matches) {
        for (const m of matches) {
          issues.push({
            level: rule.level,
            category: rule.category,
            message: rule.description,
            file: file.path,
            line: m.line || undefined,
            snippet: m.snippet,
          })
        }
      }
    }
  }

  // 统计
  const summary = { critical: 0, high: 0, medium: 0, low: 0, info: 0 }
  for (const issue of issues) {
    summary[issue.level]++
  }

  // 判定
  let verdict: ScanResult['verdict'] = 'safe'
  if (summary.critical > 0) verdict = 'danger'
  else if (summary.high > 0) verdict = 'caution'
  else if (summary.medium > 2) verdict = 'caution'

  return { fileCount: files.length, issues, summary, verdict }
}

// ─── 导出 ─────────────────────────────────

/** GitHub 仓库信誉检查结果 */
export interface GitHubRepoCheck {
  stars: number
  forks: number
  lastPush: string
  openIssues: number
  warnings: string[]
  verdict: 'trusted' | 'caution' | 'unknown'
}

/**
 * 检查 GitHub 仓库信誉（需要网络请求，单独调用）
 * @param repo "user/repo" 格式
 */
export async function checkGitHubRepo(repo: string): Promise<GitHubRepoCheck> {
  const warnings: string[] = []
  try {
    const resp = await fetch(`https://api.github.com/repos/${repo}`)
    if (!resp.ok) {
      return { stars: 0, forks: 0, lastPush: '', openIssues: 0, warnings: ['无法获取仓库信息'], verdict: 'unknown' }
    }
    const data = await resp.json()
    const stars = data.stargazers_count ?? 0
    const forks = data.forks_count ?? 0
    const lastPush = data.pushed_at ?? ''
    const openIssues = data.open_issues_count ?? 0

    if (stars < 5) warnings.push(`⭐ 仅 ${stars} 星，知名度低`)
    if (forks < 2) warnings.push(`🍴 仅 ${forks} 个 fork，社区参与度低`)

    // 最后推送超过 6 个月
    if (lastPush) {
      const monthsAgo = (Date.now() - new Date(lastPush).getTime()) / (1000 * 60 * 60 * 24 * 30)
      if (monthsAgo > 6) warnings.push(`📅 最后更新于 ${Math.floor(monthsAgo)} 个月前，可能已废弃`)
    }

    let verdict: GitHubRepoCheck['verdict'] = 'trusted'
    if (warnings.length >= 2) verdict = 'caution'
    if (stars === 0 && forks === 0) verdict = 'unknown'

    return { stars, forks, lastPush, openIssues, warnings, verdict }
  } catch {
    return { stars: 0, forks: 0, lastPush: '', openIssues: 0, warnings: ['网络请求失败'], verdict: 'unknown' }
  }
}

export async function parseSkillFolder(fileList: FileList): Promise<SkillFolderParsed> {
  const files = Array.from(fileList)
  const firstPath = files[0]?.webkitRelativePath ?? ''
  const folderName = firstPath.split('/')[0] || 'unnamed-skill'

  // 读取所有文件
  const fileContents: FileWithMeta[] = []
  for (const file of files) {
    const relativePath = file.webkitRelativePath.replace(`${folderName}/`, '')
    const textContent = await readAsText(file).catch(() => '')
    const base64Content = await readAsBase64(file).catch(() => '')
    fileContents.push({ path: relativePath, content: base64Content, decodedContent: textContent, size: file.size })
  }

  // 解析 SKILL.md
  const skillMdFile = fileContents.find((f) => f.path === 'SKILL.md')
  let frontmatter: SkillFrontmatter = {}
  let bodyDescription: string | undefined
  if (skillMdFile) {
    frontmatter = parseFrontmatter(skillMdFile.decodedContent)
    bodyDescription = extractDescriptionFromBody(skillMdFile.decodedContent)
  }

  // 解析 metadata.json
  let metadata: SkillMetadata = {}
  const metadataFile = fileContents.find((f) => f.path === 'metadata.json')
  if (metadataFile) {
    metadata = parseMetadataJson(metadataFile.decodedContent)
  }

  // 安全扫描
  const scanResult = runScan(fileContents)

  return {
    folderName,
    extractedName: frontmatter.name,
    extractedDescription: frontmatter.description ?? bodyDescription,
    extractedVersion: metadata.version,
    extractedTriggerWords: frontmatter.triggerWords,
    extractedDependencies: metadata.dependencies,
    files: fileContents.map(({ path, content }) => ({ path, content })),
    scanResult,
  }
}
