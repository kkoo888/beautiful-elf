import { Tabs } from 'antd'
import { HistoryOutlined, NodeIndexOutlined, BulbOutlined } from '@ant-design/icons'
import CorrectionHistory from './components/correction-history'
import PatternDisplay from './components/pattern-display'
import SkillSuggestion from './components/skill-suggestion'
import styles from './intent-learning-panel.module.css'

const items = [
  {
    key: 'corrections',
    label: (
      <span>
        <HistoryOutlined /> 纠正历史
      </span>
    ),
    children: <CorrectionHistory />,
  },
  {
    key: 'patterns',
    label: (
      <span>
        <NodeIndexOutlined /> 行为模式
      </span>
    ),
    children: <PatternDisplay />,
  },
  {
    key: 'suggestions',
    label: (
      <span>
        <BulbOutlined /> 技能建议
      </span>
    ),
    children: <SkillSuggestion />,
  },
]

export default function IntentLearningPanel() {
  return (
    <div className={styles.panel}>
      <Tabs items={items} defaultActiveKey="corrections" />
    </div>
  )
}
