/** 离线面板 */

import { NetworkBanner } from './components/network-banner'
import { OfflineStats } from './components/offline-stats'
import styles from './offline-panel.module.css'

export default function OfflinePanel() {
  return (
    <div className={styles.panel}>
      <h2 className={styles.title}>📡 网络 & 离线存储</h2>
      <NetworkBanner />
      <OfflineStats />
    </div>
  )
}
