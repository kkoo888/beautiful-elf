export interface BackupRecord {
  id: number
  backupType: number // 0=MySQL, 1=Redis, 2=全量
  filePath: string
  fileSize: number
  status: number // 0=进行中, 1=成功, 2=失败
  errorMessage: string
  createdAt: string
  updatedAt: string
}
