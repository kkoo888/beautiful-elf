import { ConfigProvider, theme, type ThemeConfig } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import { useThemePersist } from '@/hooks/use-theme-persist'
import type { ThemeMode } from '@/types'

/**
 * 自定义 Design Token
 * 遵循 CONVENTIONS.md：温暖橙黄主色，柔和蓝绿辅助色，8px 圆角
 */
const lightToken: ThemeConfig = {
  algorithm: theme.defaultAlgorithm,
  token: {
    colorPrimary: '#E8913A', // 温暖橙色
    colorSuccess: '#52C41A',
    colorWarning: '#FAAD14',
    colorError: '#FF4D4F',
    colorInfo: '#3BA0E8', // 柔和蓝色
    borderRadius: 8,
    fontSize: 14,
    colorBgContainer: '#FAFAFA',
    colorBgLayout: '#F5F5F5',
    fontFamily:
      "-apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', 'Inter', sans-serif",
  },
}

const darkToken: ThemeConfig = {
  algorithm: theme.darkAlgorithm,
  token: {
    colorPrimary: '#E8913A',
    colorSuccess: '#52C41A',
    colorWarning: '#FAAD14',
    colorError: '#FF4D4F',
    colorInfo: '#3BA0E8',
    borderRadius: 8,
    fontSize: 14,
    colorBgContainer: '#1A1A1A',
    colorBgLayout: '#141414',
    fontFamily:
      "-apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', 'Inter', sans-serif",
  },
}

/**
 * 获取主题配置
 */
function getThemeConfig(mode: ThemeMode): ThemeConfig {
  switch (mode) {
    case 'dark':
      return darkToken
    case 'high-contrast':
      return {
        ...lightToken,
        algorithm: theme.defaultAlgorithm,
        token: {
          ...lightToken.token,
          colorPrimary: '#0050B3',
          colorBgContainer: '#FFFFFF',
          colorTextBase: '#000000',
        },
      }
    default:
      return lightToken
  }
}

interface ThemeProviderProps {
  children: React.ReactNode
}

/**
 * 主题提供者
 * 封装 Ant Design ConfigProvider，统一管理主题 Token
 * 使用 useThemePersist 实现主题持久化与跨窗口同步
 */
export function ThemeProvider({ children }: ThemeProviderProps) {
  const { theme: themeMode } = useThemePersist()
  const themeConfig = getThemeConfig(themeMode)

  return (
    <ConfigProvider locale={zhCN} theme={themeConfig}>
      {children}
    </ConfigProvider>
  )
}
