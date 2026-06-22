/** 搜索 + 筛选工具栏 — 搜索框 + 实体类型筛选 */

import { Input, Segmented } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import { useGraphStore } from './graph-store'

const ENTITY_TYPE_OPTIONS = [
  { label: '全部', value: 'all' },
  { label: '👤 人物', value: 'person' },
  { label: '🛠 技术', value: 'tech' },
  { label: '📁 项目', value: 'project' },
  { label: '🔧 工具', value: 'tool' },
  { label: '💡 概念', value: 'concept' },
  { label: '🏢 组织', value: 'org' },
]

export function GraphToolbar() {
  const { searchKeyword, setSearchKeyword, entityTypeFilter, setEntityTypeFilter } = useGraphStore()

  return (
    <div style={{
      position: 'absolute', top: 8, left: 8, right: 8, zIndex: 10,
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      gap: 8, pointerEvents: 'none',
    }}>
      <Input
        placeholder="搜索实体..."
        prefix={<SearchOutlined style={{ color: '#bfbfbf' }} />}
        value={searchKeyword}
        onChange={e => setSearchKeyword(e.target.value)}
        allowClear
        style={{
          width: 200, background: 'rgba(255,255,255,0.92)',
          borderRadius: 6, boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
          pointerEvents: 'auto',
        }}
        size="small"
      />

      <Segmented
        value={entityTypeFilter}
        onChange={v => setEntityTypeFilter(v as string)}
        options={ENTITY_TYPE_OPTIONS}
        size="small"
        style={{
          background: 'rgba(255,255,255,0.92)',
          boxShadow: '0 1px 4px rgba(0,0,0,0.06)',
          borderRadius: 6,
          pointerEvents: 'auto',
        }}
      />
    </div>
  )
}
