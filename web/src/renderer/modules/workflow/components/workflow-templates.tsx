/** 模板库组件 */

import { Card, Typography, Spin, Tag } from 'antd'
import type { WorkflowTemplate } from '../types/workflow'
import { EmptyState } from '@/components/empty-state'
import styles from './workflow-panel.module.css'

const { Paragraph } = Typography

interface WorkflowTemplatesProps {
  templates: WorkflowTemplate[]
  loading?: boolean
  onUseTemplate: (templateId: string) => void
}

export function WorkflowTemplates({ templates, loading, onUseTemplate }: WorkflowTemplatesProps) {
  if (loading) {
    return <Spin style={{ display: 'block', textAlign: 'center', padding: 48 }} />
  }

  if (templates.length === 0) {
    return <EmptyState icon="📦" description="暂无模板" />
  }

  return (
    <div className={styles.templateGrid}>
      {templates.map((tpl) => (
        <Card
          key={tpl.id}
          className={styles.templateCard}
          hoverable
          onClick={() => onUseTemplate(tpl.id)}
        >
          <div className={styles.templateIcon}>{tpl.icon}</div>
          <Card.Meta
            title={tpl.name}
            description={
              <>
                <Tag className={styles.templateCategory}>{tpl.category}</Tag>
                <Paragraph type="secondary" style={{ fontSize: 13, marginBottom: 0 }}>
                  {tpl.description}
                </Paragraph>
                <Tag style={{ marginTop: 8 }}>{tpl.nodes.length} 个节点</Tag>
              </>
            }
          />
        </Card>
      ))}
    </div>
  )
}
