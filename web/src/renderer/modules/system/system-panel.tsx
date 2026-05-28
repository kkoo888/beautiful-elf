/** 系统面板 */

import { Tabs } from 'antd'
import { SettingOutlined } from '@ant-design/icons'
import { HotkeySettings } from './components/hotkey-settings'
import styles from './system-panel.module.css'

export default function SystemPanel() {
  return (
    <div className={styles.panel}>
      <h2 className={styles.title}>⚙️ 系统设置</h2>
      <Tabs
        items={[
          {
            key: 'hotkeys',
            label: '⌨️ 快捷键',
            children: <HotkeySettings />,
          },
        ]}
      />
    </div>
  )
}
