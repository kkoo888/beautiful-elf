/** 灵魂系统类型定义 */

export interface SoulOnboardData {
  /** 步骤索引 */
  step: number
  /** 助手名称 */
  name: string
  /** 头像 */
  avatar: string
  /** 性格标签 */
  personality: string[]
  /** 说话风格 */
  speakingStyle: string
  /** 情感倾向 */
  emotionalTendency: number
  /** 背景故事 */
  backgroundStory: string
}

export interface SoulOnboardProps {
  /** 完成引导回调 */
  onComplete: (data: SoulOnboardData) => void
  /** 跳过引导回调 */
  onSkip?: () => void
}
