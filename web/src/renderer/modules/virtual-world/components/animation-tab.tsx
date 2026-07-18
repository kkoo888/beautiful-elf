import { Button, Empty } from 'antd'
import {
  PlayCircleOutlined,
  UploadOutlined,
  VideoCameraOutlined,
  SmileOutlined,
  ManOutlined,
  CoffeeOutlined,
} from '@ant-design/icons'
import styles from '../virtual-world-panel.module.css'

const PLACEHOLDER_ANIMS = [
  { name: '待机呼吸', icon: <CoffeeOutlined />, meta: 'idle · 循环 · 2.0s' },
  { name: '行走', icon: <ManOutlined />, meta: 'walk · 循环 · 1.2s' },
  { name: '挥手打招呼', icon: <SmileOutlined />, meta: 'emote · 单次 · 1.5s' },
  { name: '舞蹈', icon: <VideoCameraOutlined />, meta: 'dance · 单次 · 8.0s' },
]

export default function AnimationTab() {
  return (
    <div className={styles.panel}>
      <div className={styles.animLayout}>
        {/* 头部 */}
        <div className={styles.animHeader}>
          <div className={styles.toolbarLeft}>
            <span className={styles.toolbarTitle}>动画库</span>
            <span className={styles.toolbarCount}>0 个动画</span>
          </div>
          <div className={styles.btnRow}>
            <Button className={styles.btnSecondary} icon={<UploadOutlined />} size="small">
              上传动画
            </Button>
            <Button className={styles.btnPrimary} icon={<PlayCircleOutlined />} size="small">
              从 Mixamo 导入
            </Button>
          </div>
        </div>

        {/* 动画网格 */}
        <div className={styles.animGrid}>
          {PLACEHOLDER_ANIMS.map((anim) => (
            <div key={anim.name} className={styles.animCard}>
              <div className={styles.animCardIcon}>{anim.icon}</div>
              <div className={styles.animCardName}>{anim.name}</div>
              <div className={styles.animCardMeta}>{anim.meta}</div>
            </div>
          ))}

          {/* 添加动画卡片 */}
          <div className={styles.animCardUpload}>
            <div className={styles.animCardUploadIcon}>
              <UploadOutlined />
            </div>
            <div className={styles.animCardUploadName}>
              上传新动画
            </div>
            <div className={styles.animCardMeta}>支持 BVH / FBX / JSON</div>
          </div>
        </div>

        {/* 提示 */}
        <div className={styles.emptyWrapCompact}>
          <div className={styles.emptyText}>
            💡 从 Mixamo 下载动画 → 上传到动画库 → 在状态机中配置过渡
          </div>
        </div>
      </div>
    </div>
  )
}
