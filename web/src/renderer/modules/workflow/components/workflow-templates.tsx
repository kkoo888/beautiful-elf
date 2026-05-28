/** 模板库组件 */

import { Card, Typography, Button, Spin, Tag } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import type { WorkflowTemplate } from '../types/workflow'
import { EmptyState } from '@/components/empty-state'
import styles from './workflow-panel.module.css'

const { Text, Paragraph } = Typography

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
          actions={[
            <Button
              key="use"
              type="link"
              icon={<PlusOutlined />}
              onClick={() => onUseTemplate(tpl.id)}
            >
              使用模板
            </Button>,
          ]}
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
                <Text type="secondary" style={{ fontSize: 12 }}>
                  {tpl.steps.length} 个步骤
                </Text>
              </>
            }
          />
        </Card>
      ))}
    </div>
  )
}
