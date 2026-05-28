import { Tag, Tooltip } from 'antd'
import { getTagColor } from '../types/snippets'

interface TagManagerProps {
  tags: string[]
  onTagClick?: (tag: string) => void
  activeTags?: string[]
  closable?: boolean
  onClose?: (tag: string) => void
}

export function TagManager({
  tags,
  onTagClick,
  activeTags = [],
  closable = false,
  onClose
}: TagManagerProps) {
  return (
    <>
      {tags.map((tag) => {
        const isActive = activeTags.includes(tag)
        return (
          <Tooltip key={tag} title={isActive ? '点击取消筛选' : '点击筛选'}>
            <Tag
              color={getTagColor(tag)}
              style={{
                cursor: onTagClick ? 'pointer' : 'default',
                opacity: activeTags.length > 0 && !isActive ? 0.5 : 1,
                border: isActive ? '2px solid currentColor' : undefined
              }}
              closable={closable}
              onClose={(e) => {
                e.preventDefault()
                onClose?.(tag)
              }}
              onClick={() => onTagClick?.(tag)}
            >
              {tag}
            </Tag>
          </Tooltip>
        )
      })}
    </>
  )
}
