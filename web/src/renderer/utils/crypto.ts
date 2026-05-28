/**
 * 简单加密工具（用于敏感配置项本地存储）
 * 注意：这不是安全加密，仅用于混淆，防止明文存储
 */

const ENCODING_KEY = 'beautiful-elf-2026'

/**
 * 简单 XOR 加密/解密
 */
function xorProcess(input: string, key: string): string {
  let result = ''
  for (let i = 0; i < input.length; i++) {
    result += String.fromCharCode(input.charCodeAt(i) ^ key.charCodeAt(i % key.length))
  }
  return result
}

/**
 * 加密字符串（Base64 编码输出）
 */
export function encrypt(plaintext: string, key = ENCODING_KEY): string {
  const encrypted = xorProcess(plaintext, key)
  return btoa(unescape(encodeURIComponent(encrypted)))
}

/**
 * 解密字符串（Base64 编码输入）
 */
export function decrypt(cipherBase64: string, key = ENCODING_KEY): string {
  const encrypted = decodeURIComponent(escape(atob(cipherBase64)))
  return xorProcess(encrypted, key)
}
