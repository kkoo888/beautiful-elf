import { Tabs } from 'antd'
import {
  ControlOutlined,
  BlockOutlined,
  BuildOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons'
import ControlTab from './components/control-tab'
import BlockRegistryTab from './components/block-registry-tab'
import SceneBuilderTab from './components/scene-builder-tab'
import AnimationTab from './components/animation-tab'
import styles from './virtual-world-panel.module.css'

const tabItems = [
  {
    key: 'control',
    label: (
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
        <ControlOutlined />
        控制台
      </span>
    ),
    children: <ControlTab />,
  },
  {
    key: 'blocks',
    label: (
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
        <BlockOutlined />
        方块库
      </span>
    ),
    children: <BlockRegistryTab />,
  },
  {
    key: 'builder',
    label: (
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
        <BuildOutlined />
        场景搭建
      </span>
    ),
    children: <SceneBuilderTab />,
  },
  {
    key: 'animation',
    label: (
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
        <PlayCircleOutlined />
        动画
      </span>
    ),
    children: <AnimationTab />,
  },
]

export default function VirtualWorldPanel() {
  return (
    <div className={styles.panelShell}>
      {/* 顶栏 */}
      <div className={styles.topBar}>
        <div className={styles.topBarLeft}>
          <div className={styles.topBarIcon}>🌍</div>
          <div>
            <div className={styles.topBarTitle}>虚拟世界</div>
            <div className={styles.topBarSub}>用积木搭建你的宠物家园</div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className={styles.tabWrap}>
        <Tabs
          items={tabItems}
          defaultActiveKey="control"
          size="small"
          tabBarGutter={20}
        />
      </div>
    </div>
  )
}
