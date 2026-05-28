import { Input } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import styles from './clipboard-panel.module.css'

interface ClipboardSearchProps {
  value: string
  onChange: (value: string) => void
}

/**
 * 剪贴板搜索栏
 * 实时搜索，防抖在 useClipboard hook 中处理
 */
export function ClipboardSearch({ value, onChange }: ClipboardSearchProps) {
  return (
    <div className={styles.searchBar}>
      <Input
        prefix={<SearchOutlined />}
        placeholder="搜索剪贴板内容..."
        allowClear
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={styles.searchInput}
      />
    </div>
  )
}
