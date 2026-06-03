/**
 * 技能文件夹解析工具
 *
 * 从用户选择的文件夹中提取 SKILL.md 和 metadata.json，
 * 解析出技能名称、描述、版本、触发词、依赖等元数据。
 */

import type { SkillFolderParsed } from '../types/skills'

/** SKILL.md frontmatter 解析结果 */
interface SkillFrontmatter {
  name?: string
  description?: string
  triggerWords?: string[]
}

/** metadata.json 解析结果 */
interface SkillMetadata {
  version?: string
  dependencies?: string[]
}

/**
 * 读取 File 对象为文本
 */
function readAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = reject
    reader.readAsText(file)
  })
}

/**
 * 读取 File 对象为 base64
 */
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

/**
 * 解析 SKILL.md 的 YAML frontmatter
 *
 * 支持格式:
 * ---
 * name: xxx
 * description: xxx
 * ---
 */
function parseFrontmatter(content: string): SkillFrontmatter {
  const result: SkillFrontmatter = {}

  // 匹配 frontmatter 块
  const match = content.match(/^---\s*\n([\s\S]*?)\n---/)
  if (!match) return result

  const yaml = match[1]

  // 简单 YAML 解析（不引入完整解析器）
  const nameMatch = yaml.match(/^name:\s*(.+)$/m)
  if (nameMatch) result.name = nameMatch[1].trim().replace(/^['"]|['"]$/g, '')

  const descMatch = yaml.match(/^description:\s*(.+)$/m)
  if (descMatch) result.description = descMatch[1].trim().replace(/^['"]|['"]$/g, '')

  // 触发词：支持 YAML 数组格式 [a, b, c] 或逗号分隔
  const triggerMatch = yaml.match(/^trigger_words:\s*(.+)$/m)
  if (triggerMatch) {
    const raw = triggerMatch[1].trim()
    if (raw.startsWith('[')) {
      result.triggerWords = raw
        .slice(1, -1)
        .split(',')
        .map((w) => w.trim().replace(/^['"]|['"]$/g, ''))
        .filter(Boolean)
    } else {
      result.triggerWords = raw
        .split(',')
        .map((w) => w.trim().replace(/^['"]|['"]$/g, ''))
        .filter(Boolean)
    }
  }

  return result
}

/**
 * 从 SKILL.md 正文中提取描述（frontmatter 之后的第一段非空文本）
 */
function extractDescriptionFromBody(content: string): string | undefined {
  // 跳过 frontmatter
  const afterFrontmatter = content.replace(/^---\s*\n[\s\S]*?\n---\s*\n?/, '')
  // 取第一个非空段落
  const lines = afterFrontmatter.split('\n')
  const descLines: string[] = []
  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) {
      if (descLines.length > 0) break
      continue
    }
    // 跳过标题行
    if (trimmed.startsWith('#')) {
      if (descLines.length > 0) break
      continue
    }
    descLines.push(trimmed)
  }
  return descLines.length > 0 ? descLines.join(' ') : undefined
}

/**
 * 解析 metadata.json
 */
function parseMetadataJson(content: string): SkillMetadata {
  try {
    const data = JSON.parse(content)
    return {
      version: data.version ?? data['version'],
      dependencies: data.dependencies ?? data['dependencies'],
    }
  } catch {
    return {}
  }
}

/**
 * 从 FileList（webkitdirectory 选中的文件夹）中解析技能元数据
 *
 * @param fileList - 浏览器 FileList 对象（webkitdirectory 模式）
 * @returns 解析结果，包含元数据和文件内容
 */
export async function parseSkillFolder(fileList: FileList): Promise<SkillFolderParsed> {
  const files = Array.from(fileList)

  // 提取文件夹名：webkitdirectory 的第一个文件的 relativePath 格式为 "folderName/..."
  const firstPath = files[0]?.webkitRelativePath ?? ''
  const folderName = firstPath.split('/')[0] || 'unnamed-skill'

  // 找到 SKILL.md 和 metadata.json
  const skillMdFile = files.find((f) => {
    const parts = f.webkitRelativePath.split('/')
    return parts[parts.length - 1] === 'SKILL.md'
  })
  const metadataFile = files.find((f) => {
    const parts = f.webkitRelativePath.split('/')
    return parts[parts.length - 1] === 'metadata.json'
  })

  // 解析 SKILL.md
  let frontmatter: SkillFrontmatter = {}
  let bodyDescription: string | undefined
  if (skillMdFile) {
    const content = await readAsText(skillMdFile)
    frontmatter = parseFrontmatter(content)
    bodyDescription = extractDescriptionFromBody(content)
  }

  // 解析 metadata.json
  let metadata: SkillMetadata = {}
  if (metadataFile) {
    const content = await readAsText(metadataFile)
    metadata = parseMetadataJson(content)
  }

  // 读取所有文件内容
  const fileContents = await Promise.all(
    files.map(async (file) => ({
      path: file.webkitRelativePath.replace(`${folderName}/`, ''),
      content: await readAsBase64(file),
    }))
  )

  return {
    folderName,
    extractedName: frontmatter.name,
    extractedDescription: frontmatter.description ?? bodyDescription,
    extractedVersion: metadata.version,
    extractedTriggerWords: frontmatter.triggerWords,
    extractedDependencies: metadata.dependencies,
    files: fileContents,
  }
}
