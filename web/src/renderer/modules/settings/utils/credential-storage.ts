/**
 * 记住账号密码 - 本地加密存储
 * 方案 A：XOR + Base64 混淆（Electron 本地环境够用，非公网场景）
 */

const ENC_KEY = 'beautiful-elf-cred-v1'
const CRED_KEY = 'beautiful-elf:saved_credentials'

function xorEncrypt(text: string, key: string): string {
  let result = ''
  for (let i = 0; i < text.length; i++) {
    result += String.fromCharCode(text.charCodeAt(i) ^ key.charCodeAt(i % key.length))
  }
  return btoa(result)
}

function xorDecrypt(encoded: string, key: string): string {
  const text = atob(encoded)
  let result = ''
  for (let i = 0; i < text.length; i++) {
    result += String.fromCharCode(text.charCodeAt(i) ^ key.charCodeAt(i % key.length))
  }
  return result
}

interface SavedCredentials {
  username: string
  password: string
}

export function saveCredentials(username: string, password: string): void {
  const encrypted = xorEncrypt(JSON.stringify({ username, password }), ENC_KEY)
  localStorage.setItem(CRED_KEY, encrypted)
}

export function loadCredentials(): SavedCredentials | null {
  try {
    const encrypted = localStorage.getItem(CRED_KEY)
    if (!encrypted) return null
    const decrypted = xorDecrypt(encrypted, ENC_KEY)
    const parsed = JSON.parse(decrypted)
    if (parsed.username && parsed.password) return parsed
    return null
  } catch {
    return null
  }
}

export function clearCredentials(): void {
  localStorage.removeItem(CRED_KEY)
}
