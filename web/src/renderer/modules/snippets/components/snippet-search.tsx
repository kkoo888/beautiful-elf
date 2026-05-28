import { Input, Select, Space } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import styles from './snippets-panel.module.css'

interface SnippetSearchProps {
  keyword: string
  onKeywordChange: (keyword: string) => void
  selectedTags: string[]
  onTagsChange: (tags: string[]) => void
  allTags: string[]
}

export function SnippetSearch({
  keyword,
  onKeywordChange,
  selectedTags,
  onTagsChange,
  allTags,
}: SnippetSearchProps) {
  return (
    <Space className={styles.searchBar} size={12} wrap>
      <Input
        prefix={<SearchOutlined />}
        placeholder="搜索标题、内容、标签..."
        value={keyword}
        onChange={(e) => onKeywordChange(e.target.value)}
        allowClear
        className={styles.searchInput}
      />
      <Select
        mode="multiple"
        placeholder="按标签筛选"
        value={selectedTags}
        onChange={onTagsChange}
        options={allTags.map((t) => ({ label: t, value: t }))}
        className={styles.tagFilter}
        maxTagCount="responsive"
        allowClear
      />
    </Space>
  )
}
