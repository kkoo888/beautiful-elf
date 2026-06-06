import { PageHeader } from '@/components/page-header'
import { TranslatePanel as TranslatePanelContent } from './components/translate-panel'

/** 翻译模块面板 */
export default function TranslatePanel() {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <PageHeader title="🌐 翻译" description="智能翻译与术语管理" />
      <div style={{ flex: 1, minHeight: 0 }}>
        <TranslatePanelContent />
      </div>
    </div>
  )
}
