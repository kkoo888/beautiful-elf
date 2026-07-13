import { Tabs } from 'antd'
import { SettingOutlined, HeartOutlined, ControlOutlined } from '@ant-design/icons'
import PetControlTab from './components/pet-control-tab'
import PetStatusTab from './components/pet-status-tab'
import PetSettingsTab from './components/pet-settings-tab'
import styles from './pet-panel.module.css'

const items = [
  {
    key: 'control',
    label: (
      <span>
        <ControlOutlined /> 控制面板
      </span>
    ),
    children: <PetControlTab />,
  },
  {
    key: 'status',
    label: (
      <span>
        <HeartOutlined /> 属性&互动
      </span>
    ),
    children: <PetStatusTab />,
  },
  {
    key: 'settings',
    label: (
      <span>
        <SettingOutlined /> 设置
      </span>
    ),
    children: <PetSettingsTab />,
  },
]

export default function PetPanel() {
  return (
    <div className={styles.panelShell}>
      <Tabs items={items} defaultActiveKey="control" />
    </div>
  )
}
