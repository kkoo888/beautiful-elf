import { TranslatePanel as TranslatePanelContent } from './components/translate-panel'

/** 翻译模块面板 */
export default function TranslatePanel() {
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ flex: 1, minHeight: 0 }}>
        <TranslatePanelContent />
      </div>
    </div>
  )
}
