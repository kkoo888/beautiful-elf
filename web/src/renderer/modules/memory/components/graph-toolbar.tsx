/** 搜索 + 筛选工具栏 — 顶部搜索 + 分类快速过滤 */

import { Input, Segmented, Space } from 'antd'
import { SearchOutlined } from '@ant-design/icons'
import { useGraphStore } from './graph-store'

const CATEGORY_OPTIONS = [
  { label: '全部', value: 'all' },
  { label: '🔑 决策', value: 'decisions' },
  { label: '🐛 踩坑', value: 'pitfalls' },
  { label: '👤 偏好', value: 'preferences' },
  { label: '📦 状态', value: 'status' },
]

export function GraphToolbar() {
  const { searchKeyword, setSearchKeyword, categoryFilter, setCategoryFilter } = useGraphStore()

  return (
    <div style={{
      position: 'absolute', top: 8, left: 8, right: 8, zIndex: 10,
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      gap: 8, pointerEvents: 'none',
    }}>
      {/* 搜索框 */}
      <Input
        placeholder="搜索节点..."
        prefix={<SearchOutlined style={{ color: '#bfbfbf' }} />}
        value={searchKeyword}
        onChange={e => setSearchKeyword(e.target.value)}
        allowClear
        style={{
          width: 200, background: 'rgba(255,255,255,0.95)',
          borderRadius: 8, boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
          pointerEvents: 'auto',
        }}
        size="small"
      />

      {/* 分类筛选 */}
      <Segmented
        value={categoryFilter}
        onChange={v => setCategoryFilter(v as string)}
        options={CATEGORY_OPTIONS}
        size="small"
        style={{
          background: 'rgba(255,255,255,0.95)',
          boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
          borderRadius: 8,
          pointerEvents: 'auto',
        }}
      />
    </div>
  )
}
