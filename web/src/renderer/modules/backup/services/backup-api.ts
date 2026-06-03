/**
 * 备份 API 服务
 */

import { apiClient, extractData, extractPaginated } from '@/services/api-client'
import type { BackupRecord } from '../types/backup'

export async function createBackup(data: {
  backupType: number; filePath: string; fileSize: number; status: number; errorMessage: string
}): Promise<BackupRecord> {
  return extractData(await apiClient.post('/backups/', data))
}

export async function fetchBackups(params: {
  page?: number; pageSize?: number; backupType?: number; status?: number
} = {}): Promise<{ items: BackupRecord[]; total: number }> {
  const { items, total } = extractPaginated(await apiClient.get('/backups/', { params }) as any)
  return { items, total }
}

export async function fetchBackupById(id: number): Promise<BackupRecord> {
  return extractData(await apiClient.get(`/backups/${id}`))
}

export async function updateBackupStatus(
  id: number, data: { status: number; errorMessage?: string; fileSize?: number }
): Promise<BackupRecord> {
  return extractData(await apiClient.patch(`/backups/${id}/status`, data))
}
