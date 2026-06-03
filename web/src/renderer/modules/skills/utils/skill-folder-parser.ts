/**
 * 技能文件夹解析 + 安全扫描工具
 *
 * 26 项检测规则，基于 skill-vetter / skill-security-scanner / CertiK 合集。
 * 纯前端正则实现，无需后端接口。
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
  // HIGH
  ruleExfiltration, rulePersistence, rulePrivilegeEscalation, ruleObfuscation, ruleMemoryAccess, ruleBrowserTheft, ruleSilentInstall,
  // MEDIUM
  ruleBase64Payload, ruleAnomalousNetwork, ruleRawIP, ruleHighEntropy, ruleDangerousShell, ruleEnvReading, ruleFileOverreach, ruleProcessOps,
  // LOW
  ruleHiddenChars, rulePermissionMismatch,
]

// ─── 主扫描函数 ─────────────────────────────────

function runScan(files: { path: string; decodedContent: string }[]): ScanResult {
  const issues: ScanIssue[] = []
  let hasSkillMd = false

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

  // 遍历所有文件执行规则
  for (const file of files) {
    for (const rule of ALL_RULES) {
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

export async function parseSkillFolder(fileList: FileList): Promise<SkillFolderParsed> {
  const files = Array.from(fileList)
  const firstPath = files[0]?.webkitRelativePath ?? ''
  const folderName = firstPath.split('/')[0] || 'unnamed-skill'

  // 读取所有文件
  const fileContents: { path: string; content: string; decodedContent: string }[] = []
  for (const file of files) {
    const relativePath = file.webkitRelativePath.replace(`${folderName}/`, '')
    const textContent = await readAsText(file).catch(() => '')
    const base64Content = await readAsBase64(file).catch(() => '')
    fileContents.push({ path: relativePath, content: base64Content, decodedContent: textContent })
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
