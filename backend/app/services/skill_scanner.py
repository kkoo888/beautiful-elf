"""技能安全扫描引擎 — 36 条规则 + 结构分析

基于 skill-vetter / OWASP Agentic AI / CSA MAESTRO。
对技能文件夹进行全面安全扫描，返回分级风险报告。
"""
import re
import os
import json
from dataclasses import dataclass, field
from typing import List, Optional


# ─── 数据结构 ─────────────────────────────────────

@dataclass
class ScanIssue:
    level: str          # critical | high | medium | low | info
    category: str
    message: str
    file: Optional[str] = None
    line: Optional[int] = None
    snippet: Optional[str] = None


@dataclass
class ScanResult:
    file_count: int
    issues: List[ScanIssue] = field(default_factory=list)
    summary: dict = field(default_factory=lambda: {
        "critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0,
    })
    verdict: str = "safe"  # safe | caution | danger


# ─── 工具函数 ─────────────────────────────────────

def _find_matches(content: str, pattern: re.Pattern,
                  file_filter: Optional[re.Pattern] = None,
                  file_path: str = "") -> list[dict]:
    """按行查找正则匹配"""
    if file_filter and not file_filter.search(file_path):
        return []
    results = []
    for i, line in enumerate(content.split("\n"), 1):
        if pattern.search(line):
            results.append({"line": i, "snippet": line.strip()[:120]})
    return results


def _find_global(content: str, pattern: re.Pattern) -> list[dict]:
    """全文匹配（不分行）"""
    m = pattern.search(content)
    if not m:
        return []
    return [{"line": 0, "snippet": m.group()[:120]}]


# ─── 可执行文件扩展名 ─────────────────────────────

EXECUTABLE_EXTENSIONS = {
    ".sh", ".bash", ".zsh", ".fish", ".csh", ".ksh",
    ".py", ".pyc", ".pyw",
    ".js", ".mjs", ".cjs",
    ".ts", ".tsx", ".mts",
    ".rb", ".pl", ".lua", ".php", ".r", ".R",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".com", ".msi",
    ".bat", ".cmd", ".ps1", ".psm1", ".vbs", ".vba", ".wsf", ".jse",
    ".jar", ".class", ".war",
    ".go", ".rs", ".swift", ".kt", ".scala",
    ".appimage", ".deb", ".rpm", ".dmg", ".pkg",
}

SUSPICIOUS_FILENAMES = [
    re.compile(r"^\.[^/]+\.(sh|bash|py|js|ts|rb|pl|exe|bat|ps1|cmd|vbs|dll|so)$", re.I),
    re.compile(r"\.(bak|old|tmp|swp)$"),
    re.compile(r"\.(enc|gpg|pgp)$"),
    re.compile(r"__MACOSX"),
    re.compile(r"Thumbs\.db$", re.I),
]

TEXT_EXTENSIONS = {".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".xml", ".csv", ".log"}


# ═══════════════════════════════════════════════════
#  规则定义
# ═══════════════════════════════════════════════════

_EXEC_FILTER = re.compile(r"\.[\w]+$", re.I)
_MD_FILTER = re.compile(r"\.md$", re.I)

# ── CRITICAL（6 项）────────────────────────────────

_RULES_CRITICAL = [
    {
        "id": "remote-exec", "category": "远程下载执行", "level": "critical",
        "desc": "检测从远程地址下载文件并直接执行的恶意行为",
        "pattern": re.compile(r"curl\s+.*\|\s*(ba)?sh|wget\s+.*\|\s*(ba)?sh|curl\s+.*-o\s+.*&&.*sh|Invoke-WebRequest.*\|.*Invoke-Expression", re.I),
        "filter": _EXEC_FILTER,
    },
    {
        "id": "injection", "category": "命令注入", "level": "critical",
        "desc": "检测 eval/exec/os.system 等动态执行 + 命令注入",
        "pattern": re.compile(r"\beval\s*\(|\bexec\s*\(|\bos\.system\s*\(|\bos\.popen\s*\(|\bsubprocess\.(call|run|Popen)\s*\(|\bchild_process\b|\b__import__\s*\(|\bFunction\s*\(", re.I),
        "filter": _EXEC_FILTER,
    },
    {
        "id": "secrets", "category": "硬编码密钥", "level": "critical",
        "desc": "检测硬编码的 API key、token、密码等敏感凭证",
        "pattern": re.compile(r"(api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token|password|passwd|credential)\s*[:=]\s*['\"][^'\"]{8,}['\"]", re.I),
        "filter": _EXEC_FILTER,
    },
    {
        "id": "credential-theft", "category": "凭证窃取", "level": "critical",
        "desc": "检测读取 ~/.ssh、~/.aws、~/.config 等敏感路径",
        "pattern": re.compile(r"(cat|read|load|open|ls|cp|mv|rm|curl|wget|source|\.)\s+(~/\.ssh|~/\.aws|~/\.config|~/\.gnupg|~/\.docker)|/etc/(shadow|passwd)[^a-zA-Z]|\.env\b.*(?:read|cat|load|source)|credentials?\s*file", re.I),
    },
    {
        "id": "reverse-shell", "category": "反弹 Shell", "level": "critical",
        "desc": "检测建立反向 Shell 连接的行为",
        "pattern": re.compile(r"bash\s+-i\s+>&|/dev/tcp/|nc\s+.*-e|ncat\s+.*-e|socat\s+.*exec|mkfifo.*\/tmp|python.*socket.*connect|python.*subprocess.*shell", re.I),
    },
    {
        "id": "prompt-injection", "category": "Prompt 注入", "level": "critical",
        "desc": "检测试图覆盖 Agent 指令的 Prompt 注入",
        "pattern": re.compile(r"ignore\s+(all\s+)?previous\s+instructions|you\s+are\s+now\s+root|pretend\s+to\s+be\s+(admin|root|developer)|DAN\s+mode|jailbreak|override\s+(all\s+)?safety|forget\s+(all\s+)?rules|disregard\s+(all\s+)?prior|new\s+instructions?\s*[:：]|system\s*[:：]\s*you\s+are", re.I),
        "filter": _MD_FILTER,
    },
]

# ── HIGH（12 项）────────────────────────────────

_RULES_HIGH = [
    {
        "id": "exfiltration", "category": "数据外传", "level": "high",
        "desc": "检测向外部服务器上传/发送敏感数据",
        "pattern": re.compile(r"requests\.(post|put|patch)\s*\(|axios\.(post|put|patch)\s*\(|fetch\s*\([^)]*method\s*:\s*['\"]POST|httpx\.(post|put)\s*\(|urllib.*POST|\.upload\s*\(|\.send\s*\([^)]*data", re.I),
        "filter": _EXEC_FILTER,
    },
    {
        "id": "persistence", "category": "持久化后门", "level": "high",
        "desc": "检测写入自启动、计划任务、系统服务等持久化行为",
        "pattern": re.compile(r"crontab\s+(-[elru]|--)|systemctl\s+(enable|daemon-reload|start)\s+|/etc/init\.d/[a-z]|echo\s+[^|]*>>\s*~?/.*\.(bashrc|zshrc|profile)|launchctl\s+(load|write|start)\s+|schtasks\s+/(create|change)\s+|/Library\/Launch(Daemons|Agents)/|systemd\s+daemon-reload|>>\s*rc\.local", re.I),
    },
    {
        "id": "privilege-escalation", "category": "权限提升", "level": "high",
        "desc": "检测越权操作、提权行为",
        "pattern": re.compile(r"\bsudo\s+(apt|yum|dnf|pip|npm|brew|rm|cp|mv|chmod|chown|mount|umount|systemctl|service|useradd|usermod|passwd|visudo|cat|echo|tee|bash|sh|python|node)|\bchmod\s+[0-7]{3,4}\s+\b|\bchown\s+[a-z]+:[a-z]+\s+\b|\bsetuid\b|\bsetgid\b|/proc/self/exe", re.I),
    },
    {
        "id": "obfuscation", "category": "代码混淆", "level": "high",
        "desc": "检测字符串加密、动态构造等代码混淆技术",
        "pattern": re.compile(r"\\x[0-9a-f]{2}\\x[0-9a-f]{2}\\x[0-9a-f]{2}|atob\s*\(|String\.fromCharCode|charCodeAt|fromCharCode|\bBuffer\.from\s*\([^)]*base64|btoa\s*\(", re.I),
        "filter": _EXEC_FILTER,
    },
    {
        "id": "memory-access", "category": "记忆/身份文件访问", "level": "high",
        "desc": "检测读取 MEMORY.md、USER.md、SOUL.md 等 Agent 敏感文件",
        "pattern": re.compile(r"MEMORY\.md|USER\.md|SOUL\.md|IDENTITY\.md|AGENTS\.md|openclaw\.json|paired\.json", re.I),
    },
    {
        "id": "browser-theft", "category": "浏览器数据窃取", "level": "high",
        "desc": "检测访问浏览器 cookies、sessions、存储数据",
        "pattern": re.compile(r"\.cookies|\.localStorage|\.sessionStorage|document\.cookie|chrome\.storage|browser\.cookies|IndexedDB|WebSQL|navigator\.credentials", re.I),
        "filter": _EXEC_FILTER,
    },
    {
        "id": "silent-install", "category": "静默安装包", "level": "high",
        "desc": "检测未声明的包安装行为",
        "pattern": re.compile(r"pip\s+install(?!\s+-r\s+requirements)|npm\s+install(?!\s+--save)|yarn\s+add|apt\s+install|brew\s+install|cargo\s+install|gem\s+install", re.I),
        "filter": _EXEC_FILTER,
    },
    {
        "id": "cli-exfiltration", "category": "CLI 工具外发数据", "level": "high",
        "desc": "检测 curl/wget/scp/rsync/nc 等 CLI 工具向外部发送数据的行为",
        "patterns": [
            re.compile(r"curl\s+[^\n]*(-d|--data|--data-raw|--data-binary|--data-urlencode|-F|--form|-T|--upload-file)\s+", re.I),
            re.compile(r"wget\s+[^\n]*--post-(data|file|body)\s+", re.I),
            re.compile(r"\b(scp|rsync)\s+[^\n]*@", re.I),
            re.compile(r"\b(nc|ncat|socat)\s+[^\n]*([<>|]|--send-only|-w)\s+", re.I),
            re.compile(r"\b(sftp|ftp|lftp)\s+[^\n]*\d{1,3}\.", re.I),
            re.compile(r"\bssh\s+[^\n]*@.*['\"`;]", re.I),
            re.compile(r"\bgit\s+push\s+(git@|https?://)", re.I),
            re.compile(r"\btelnet\s+\d{1,3}\.\d{1,3}", re.I),
        ],
    },
    {
        "id": "dns-tunnel", "category": "DNS 隧道渗出", "level": "high",
        "desc": "检测通过 DNS 查询编码数据外发的行为",
        "pattern": re.compile(r"\b(dig|nslookup|host)\s+[^\n]*\$\(|iodine|dnscat|dns2tcp|dnsinject|\bDNS_TUNNEL\b", re.I),
    },
    {
        "id": "network-sniffing", "category": "网络嗅探抓包", "level": "high",
        "desc": "检测 tcpdump/wireshark 等网络流量监听行为",
        "pattern": re.compile(r"\b(tcpdump|tshark|wireshark|ettercap|bettercap|arpspoof|dsniff)\b", re.I),
    },
    {
        "id": "container-escape", "category": "容器逃逸", "level": "high",
        "desc": "检测 Docker --privileged、挂载宿主机文件系统等容器逃逸行为",
        "pattern": re.compile(r"docker\s+run\s+[^\n]*--privileged|docker\s+run\s+[^\n]*-v\s*/:|docker\s+run\s+[^\n]*--pid=host|docker\s+run\s+[^\n]*--net=host|nsenter\s+-t\s+1|/proc/1/ns/|chroot\s+/host", re.I),
    },
    {
        "id": "supply-chain", "category": "供应链篡改", "level": "high",
        "desc": "检测向依赖文件注入可疑包的行为",
        "file_filter": re.compile(r"(package\.json|requirements.*\.txt|Gemfile|go\.mod|Cargo\.toml|pom\.xml|build\.gradle)", re.I),
        "pattern": re.compile(r"[a-z0-9]{20,}|typosquat|malware|backdoor|trojan", re.I),
    },
]

# ── MEDIUM（12 项）────────────────────────────────

_RULES_MEDIUM = [
    {
        "id": "base64-payload", "category": "Base64 编码载荷", "level": "medium",
        "desc": "检测用 Base64 编码隐藏的可疑载荷",
        "pattern": re.compile(r"['\"]([A-Za-z0-9+/]{60,}={0,2})['\"]"),
        "filter": _EXEC_FILTER,
    },
    {
        "id": "anomalous-network", "category": "异常网络请求", "level": "medium",
        "desc": "检测非标准端口或可疑域名的网络请求",
        "pattern": re.compile(r"https?://[^/]+:\d{2,5}/|\.onion\b|\.top\b|\.xyz\b|pastebin\.com|hastebin\.com|ngrok\.io|serveo\.net|localtunnel", re.I),
    },
    {
        "id": "raw-ip", "category": "裸 IP 地址", "level": "medium",
        "desc": "检测使用裸 IP 地址代替域名的网络请求",
        "pattern": re.compile(r"https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"),
    },
    {
        "id": "high-entropy", "category": "高熵字符串", "level": "medium",
        "desc": "检测可能是加密 payload 的高熵字符串",
        "pattern": re.compile(r"['\"][A-Za-z0-9+/=_\-]{80,}['\"]"),
    },
    {
        "id": "dangerous-shell", "category": "危险 Shell 命令", "level": "medium",
        "desc": "检测 rm -rf、mkfs、dd 等破坏性命令",
        "pattern": re.compile(r"\brm\s+(-[rRf]+\s+|--recursive)\s*[\/~]|mkfs\b|\bdd\s+if=|\bshred\b|\bwipefs\b|\b:(){ :\|:& };:|\bkill\s+-9\s+1\b|\bshutdown\b|\breboot\b|\binit\s+0", re.I),
    },
    {
        "id": "env-reading", "category": "环境变量读取", "level": "medium",
        "desc": "检测读取系统环境变量中的敏感信息",
        "pattern": re.compile(r"os\.environ\[|process\.env\.|getenv\s*\(\s*['\"](AWS|GOOGLE|AZURE|GITHUB|GITLAB|DOCKER|NPM|PYPI|OPENAI|ANTHROPIC|SECRET|TOKEN|KEY|PASSWORD|CREDENTIAL)", re.I),
    },
    {
        "id": "file-overreach", "category": "文件系统越权", "level": "medium",
        "desc": "检测访问工作区外的系统文件",
        "pattern": re.compile(r"/etc/hosts|/etc/resolv|/var/log|/tmp/|/root/|/home/[^/]+/|C:\\\\Users\\\\|/Library/|/Applications/", re.I),
    },
    {
        "id": "process-ops", "category": "进程操作", "level": "medium",
        "desc": "检测创建/杀死系统进程的行为",
        "pattern": re.compile(r"\bkill\s+-\d|\bpkill\b|\bxkill\b|\bfork\s*\(|\bspawn\s*\(|\bexecFile\s*\(|\bchild_process\b|\bsubprocess\b|\bos\.fork\b|\bos\.spawn\b", re.I),
        "filter": _EXEC_FILTER,
    },
    {
        "id": "webhook-exfil", "category": "Webhook 外发数据", "level": "medium",
        "desc": "检测向 webhook.site/requestbin/pipedream 等数据收集服务发送数据",
        "pattern": re.compile(r"webhook\.site|requestbin\.net|pipedream\.com|hookbin\.com|burpcollaborator|interact\.sh|canarytokens\.com|oast\.(fun|pro|dev)", re.I),
    },
    {
        "id": "screen-capture", "category": "剪贴板/屏幕截取", "level": "medium",
        "desc": "检测读取剪贴板内容或截取屏幕的行为",
        "pattern": re.compile(r"\b(xclip|xsel|pbpaste|wl-paste)\b|\b(scrot|import|gnome-screenshot|screencapture|flameshot)\b|\bxdotool\s+getactivewindow", re.I),
    },
    {
        "id": "fs-watch", "category": "文件系统监听", "level": "medium",
        "desc": "检测 inotifywait/fswatch 等文件变化监听行为",
        "pattern": re.compile(r"\b(inotifywait|inotifywatch|fswatch|watchman|entr)\b", re.I),
    },
    {
        "id": "time-bomb", "category": "时间炸弹", "level": "medium",
        "desc": "检测 sleep + 后台执行、at/cron 调度等延迟触发行为",
        "pattern": re.compile(r"\bsleep\s+\d{3,}|nohup\s+.*&|\bat\s+\d{1,2}:\d{2}|\bat\s+now\s+|\bbg\b.*\bdisown\b", re.I),
    },
    {
        "id": "encrypted-payload", "category": "加密载荷", "level": "medium",
        "desc": "检测使用 GPG/age/openssl 加密数据",
        "pattern": re.compile(r"\bgpg\s+(-e|--encrypt)|\bage\s+(-e|--encrypt)|\bopenssl\s+(enc|aes|rsa)\b", re.I),
    },
]

# ── LOW（1 项）────────────────────────────────

_RULES_LOW = [
    {
        "id": "hidden-chars", "category": "隐藏字符注入", "level": "low",
        "desc": "检测零宽字符、RTL 控制符等隐蔽注入",
        "pattern": re.compile(r"[\u200B\u200C\u200D\u200E\u200F\u202A-\u202E\u2066-\u2069\uFEFF]"),
    },
]


# ═══════════════════════════════════════════════════
#  扫描引擎
# ═══════════════════════════════════════════════════

def _scan_rule(content: str, file_path: str, rule: dict) -> list[ScanIssue]:
    """对单个文件执行单条规则"""
    issues = []
    f_filter = rule.get("filter") or rule.get("file_filter")

    # cli-exfiltration 有多个 patterns
    if "patterns" in rule:
        for pat in rule["patterns"]:
            for m in _find_matches(content, pat, f_filter, file_path):
                issues.append(ScanIssue(
                    level=rule["level"], category=rule["category"],
                    message=rule["desc"], file=file_path,
                    line=m["line"], snippet=m["snippet"],
                ))
        return issues

    pattern = rule.get("pattern")
    if not pattern:
        return []

    for m in _find_matches(content, pattern, f_filter, file_path):
        issues.append(ScanIssue(
            level=rule["level"], category=rule["category"],
            message=rule["desc"], file=file_path,
            line=m["line"], snippet=m["snippet"],
        ))
    return issues


def _get_ext(path: str) -> str:
    """获取文件扩展名（小写）"""
    dot = path.rfind(".")
    return path[dot:].lower() if dot >= 0 else ""


def scan_skill_dir(skill_dir: str) -> ScanResult:
    """扫描技能目录，返回安全报告"""
    issues: List[ScanIssue] = []
    file_count = 0
    files: List[tuple[str, str]] = []  # (relative_path, content)

    # 遍历目录读取文件
    for root, _, filenames in os.walk(skill_dir):
        for fname in filenames:
            rel_path = os.path.relpath(os.path.join(root, fname), skill_dir)
            abs_path = os.path.join(root, fname)
            file_count += 1
            try:
                with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                files.append((rel_path, content))
            except Exception:
                pass  # 二进制文件跳过

    # ── 结构检查 ──────────────────────────────────

    has_skill_md = any(
        p == "SKILL.md" or p.endswith("/SKILL.md") for p, _ in files
    )
    if not has_skill_md:
        issues.append(ScanIssue(
            level="info", category="文件结构完整性",
            message="缺少 SKILL.md 文件，可能不是标准技能包",
        ))

    # metadata.json 版本号检查
    for path, content in files:
        if path == "metadata.json" or path.endswith("/metadata.json"):
            try:
                meta = json.loads(content)
                ver = meta.get("version", "")
                if ver and not re.match(r"^\d+\.\d+\.\d+", str(ver)):
                    issues.append(ScanIssue(
                        level="info", category="版本与来源",
                        message=f"版本号格式不规范: \"{ver}\"",
                        file="metadata.json",
                    ))
            except json.JSONDecodeError:
                pass
            break

    # 可执行文件检测
    exec_files = [p for p, _ in files if _get_ext(p) in EXECUTABLE_EXTENSIONS]
    if not exec_files:
        issues.append(ScanIssue(
            level="info", category="文件结构分析",
            message="技能包不含任何可执行文件，风险较低",
        ))
    else:
        issues.append(ScanIssue(
            level="medium", category="可执行文件",
            message=f"发现 {len(exec_files)} 个可执行文件，需要重点审查",
            snippet=", ".join(exec_files)[:200],
        ))

    # 可疑文件名检测
    for path, _ in files:
        for pat in SUSPICIOUS_FILENAMES:
            if pat.search(path):
                issues.append(ScanIssue(
                    level="low", category="可疑文件名",
                    message=f"发现可疑文件: {path}",
                    file=path,
                ))
                break

    # 文件体积异常检测（> 50KB 文本文件）
    for path, content in files:
        size = len(content.encode("utf-8"))
        if size > 50 * 1024 and _get_ext(path) in TEXT_EXTENSIONS:
            issues.append(ScanIssue(
                level="medium", category="文件体积异常",
                message=f"文本文件体积异常 ({size // 1024}KB)，可能包含隐藏载荷",
                file=path,
                snippet=f"{size // 1024}KB",
            ))

    # ── 声明 vs 行为交叉检测 ──────────────────────

    skill_md_content = ""
    for path, content in files:
        if path == "SKILL.md" or path.endswith("/SKILL.md"):
            skill_md_content = content.lower()
            break

    all_content = "\n".join(c for _, c in files)

    has_network = bool(re.search(
        r"fetch\s*\(|axios\.|requests\.(get|post|put)|urllib|httpx|curl\s|wget\s|\.post\s*\(|XMLHttpRequest|WebSocket|new\s+Request",
        all_content, re.I,
    ))
    has_file_system = bool(re.search(
        r"\bfs\.(read|write|unlink|mkdir|rename|copy)|open\s*\([^)]*['\"][rw]|os\.(listdir|remove|makedirs)|pathlib|shutil",
        all_content, re.I,
    ))
    has_system_exec = bool(re.search(
        r"\bexec\s*\(|\bspawn\s*\(|\bos\.system\s*\(|\bsubprocess\b|\bchild_process\b|\bos\.popen\b",
        all_content, re.I,
    ))
    has_credential_access = bool(re.search(
        r"~/\.ssh|~/\.aws|~/\.config|\.env\b|credentials?|token|api[_-]?key|secret",
        all_content, re.I,
    ))
    has_persistence = bool(re.search(
        r"crontab|systemctl|/etc/init\.d|\.bashrc|\.zshrc|launchd|schtasks",
        all_content, re.I,
    ))

    # 行为透明度提示
    if has_network:
        issues.append(ScanIssue(level="info", category="行为透明度", message="该技能包含网络请求能力（可访问外部地址）"))
    if has_file_system:
        issues.append(ScanIssue(level="info", category="行为透明度", message="该技能包含文件系统操作能力（可读写文件）"))
    if has_system_exec:
        issues.append(ScanIssue(level="info", category="行为透明度", message="该技能包含系统命令执行能力（可执行 Shell 命令）"))
    if has_credential_access:
        issues.append(ScanIssue(level="info", category="行为透明度", message="该技能涉及凭证/密钥文件访问"))
    if has_persistence:
        issues.append(ScanIssue(level="info", category="行为透明度", message="该技能包含持久化能力（可修改自启动/计划任务）"))

    # 声明分类
    declared_simple = bool(re.search(
        r"天气|计算|格式化|翻译|笔记|提醒|timer|weather|format|note|calculator|convert|模板|template|snippet|日历|calendar|todo|备忘|字典|dict|汇率|exchange|单位换算|unit",
        skill_md_content,
    ))
    declared_data = bool(re.search(
        r"数据|分析|统计|图表|报告|chart|analysis|data|dashboard|可视化|visuali",
        skill_md_content,
    ))
    declared_content = bool(re.search(
        r"写作|文章|文档|内容|writing|content|blog|博客|markdown|编辑|edit",
        skill_md_content,
    ))
    declared_dev = bool(re.search(
        r"代码|开发|调试|测试|code|dev|debug|test|lint|review|部署|deploy|ci|cd",
        skill_md_content,
    ))

    # 交叉检测
    if declared_simple:
        if has_network:
            issues.append(ScanIssue(level="high", category="声明与实际不符",
                                    message="声明为简单工具类技能，但包含网络请求行为",
                                    snippet="声明: 简单工具 → 实际: 有网络请求"))
        if has_system_exec:
            issues.append(ScanIssue(level="critical", category="声明与实际不符",
                                    message="声明为简单工具类技能，但包含系统命令执行",
                                    snippet="声明: 简单工具 → 实际: 有 exec/system 调用"))
        if has_credential_access:
            issues.append(ScanIssue(level="critical", category="声明与实际不符",
                                    message="声明为简单工具类技能，但访问凭证/密钥文件",
                                    snippet="声明: 简单工具 → 实际: 读取 ~/.ssh/.aws 等"))

    if declared_data and has_system_exec:
        issues.append(ScanIssue(level="high", category="声明与实际不符",
                                message="声明为数据分析技能，但包含系统命令执行",
                                snippet="声明: 数据分析 → 实际: 有 exec/system 调用"))

    if declared_content and has_file_system:
        issues.append(ScanIssue(level="medium", category="声明与实际不符",
                                message="声明为内容创作技能，但包含文件系统操作",
                                snippet="声明: 内容创作 → 实际: 有文件读写操作"))

    if declared_dev and has_persistence:
        issues.append(ScanIssue(level="high", category="声明与实际不符",
                                message="声明为开发辅助技能，但包含持久化行为",
                                snippet="声明: 开发工具 → 实际: 有持久化操作"))

    if not any([declared_simple, declared_data, declared_content, declared_dev]):
        if has_credential_access:
            issues.append(ScanIssue(level="high", category="行为缺乏声明",
                                    message="SKILL.md 未说明用途，但代码访问凭证/密钥文件"))
        if has_system_exec and has_network:
            issues.append(ScanIssue(level="high", category="行为缺乏声明",
                                    message="SKILL.md 未说明用途，但同时有系统执行和网络请求"))

    # ── 规则扫描 ──────────────────────────────────

    all_rules = _RULES_CRITICAL + _RULES_HIGH + _RULES_MEDIUM + _RULES_LOW
    for path, content in files:
        for rule in all_rules:
            issues.extend(_scan_rule(content, path, rule))

    # ── 统计与判定 ────────────────────────────────

    summary = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
    for issue in issues:
        summary[issue.level] += 1

    verdict = "safe"
    if summary["critical"] > 0:
        verdict = "danger"
    elif summary["high"] > 0:
        verdict = "caution"
    elif summary["medium"] > 2:
        verdict = "caution"

    return ScanResult(
        file_count=file_count,
        issues=issues,
        summary=summary,
        verdict=verdict,
    )
