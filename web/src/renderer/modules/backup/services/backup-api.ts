import { apiClient } from '@/services/api-client'
import type { BackupRecord } from '../types/backup'

export async function createBackup(data: {
  backupType: number
  filePath: string
  fileSize: number
  status: number
  errorMessage: string
}): Promise<BackupRecord> {
  const resp = await apiClient.post('/backups/', data)
  return (resp.data as any).data
}

export async function fetchBackups(params: {
  page?: number
  pageSize?: number
  backupType?: number
  status?: number
} = {}): Promise<{ data: BackupRecord[]; total: number }> {
  const resp = await apiClient.get('/backups/', { params })
  return {
    data: (resp.data as any).data,
    total: (resp.data as any).total,
  }
}

export async function fetchBackupById(id: number): Promise<BackupRecord> {
  const resp = await apiClient.get(`/backups/${id}`)
  return (resp.data as any).data
}

export async function updateBackupStatus(
  id: number,
  data: { status: number; errorMessage?: string; fileSize?: number }
): Promise<BackupRecord> {
  const resp = await apiClient.patch(`/backups/${id}/status`, data)
  return (resp.data as any).data
}
