/** 技能管理主面板 */

import { useState, useCallback } from 'react'
import { Button, Input, Spin, Empty, Drawer, message } from 'antd'
import { PlusOutlined, SearchOutlined, ApiOutlined } from '@ant-design/icons'
import { PageHeader } from '@/components/page-header'
import { useSkills } from '../hooks/use-skills'
import type { Skill, ChainNode, InstallSkillInput, RefineResult } from '../types/skills'
import { SkillCard } from './skill-card'
import { SkillInstall } from './skill-install'
import { SkillDetail } from './skill-detail'
import { SkillRefine } from './skill-refine'
import { SkillChain } from './skill-chain'
import styles from './skills-panel.module.css'

const { Search } = Input

/** 技能管理面板 */
export default function SkillsPanel() {
  const {
    skills,
    enabledSkills,
    isLoading,
    keyword,
    setKeyword,
    filteredSkills,
    installSkillMut,
    toggleSkillMut,
    refineSkillMut,
    isMutating,
  } = useSkills()

  // 安装面板
  const [installOpen, setInstallOpen] = useState(false)

  // 详情面板
  const [detailOpen, setDetailOpen] = useState(false)
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null)

  // 炼化面板
  const [refineOpen, setRefineOpen] = useState(false)
  const [refiningSkill, setRefiningSkill] = useState<Skill | null>(null)

  // 链式配置面板
  const [chainOpen, setChainOpen] = useState(false)
  const [chainNodes, setChainNodes] = useState<ChainNode[]>([])

  // ─── 事件处理 ──────────────────────────────────────

  const handleCardClick = useCallback((skill: Skill) => {
    setSelectedSkill(skill)
    setDetailOpen(true)
  }, [])

  const handleToggle = useCallback(
    async (id: string, enabled: boolean) => {
      try {
        await toggleSkillMut(id, enabled)
      } catch {
        message.error('切换失败，请重试')
      }
    },
    [toggleSkillMut]
  )

  const handleInstall = useCallback(
    async (input: InstallSkillInput) => {
      await installSkillMut(input)
    },
    [installSkillMut]
  )

  const handleRefine = useCallback(
    async (id: string, prompt?: string): Promise<RefineResult> => {
      return refineSkillMut(id, prompt)
    },
    [refineSkillMut]
  )

  const handleOpenRefine = useCallback((skill: Skill) => {
    setDetailOpen(false)
    setRefiningSkill(skill)
    setRefineOpen(true)
  }, [])

  const handleChainChange = useCallback((nodes: ChainNode[]) => {
    setChainNodes(nodes)
  }, [])

  return (
    <div className={styles.panel}>
      {/* 头部 */}
      <PageHeader
        title="🔧 技能"
        description={`已安装 ${skills.length} 个技能，${enabledSkills.length} 个已启用`}
        extra={
          <>
            <Button icon={<ApiOutlined />} onClick={() => setChainOpen(true)}>
              链式配置
            </Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setInstallOpen(true)}>
              安装技能
            </Button>
          </>
        }
      />

      {/* 搜索栏 */}
      <div className={styles.headerActions}>
        <Search
          className={styles.searchInput}
          placeholder="搜索技能名称、描述、触发词..."
          allowClear
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          prefix={<SearchOutlined />}
          size="middle"
        />
        <span className={styles.statsTag}>{filteredSkills.length} 个技能</span>
      </div>

      {/* 技能卡片网格 */}
      {isLoading ? (
        <div className={styles.loading}>
          <Spin size="large" />
        </div>
      ) : filteredSkills.length === 0 ? (
        <div className={styles.empty}>
          <Empty description={keyword ? '没有匹配的技能' : '暂无已安装的技能'}>
            {!keyword && (
              <Button type="primary" icon={<PlusOutlined />} onClick={() => setInstallOpen(true)}>
                安装第一个技能
              </Button>
            )}
          </Empty>
        </div>
      ) : (
        <div className={styles.grid}>
          {filteredSkills.map((skill) => (
            <SkillCard
              key={skill.id}
              skill={skill}
              onToggle={handleToggle}
              onClick={handleCardClick}
            />
          ))}
        </div>
      )}

      {/* 安装面板 */}
      <SkillInstall
        open={installOpen}
        onClose={() => setInstallOpen(false)}
        onInstall={handleInstall}
        isLoading={isMutating}
      />

      {/* 详情面板 */}
      <SkillDetail
        open={detailOpen}
        skill={selectedSkill}
        onClose={() => setDetailOpen(false)}
        onRefine={handleOpenRefine}
      />

      {/* 炼化面板 */}
      <SkillRefine
        open={refineOpen}
        skill={refiningSkill}
        onClose={() => setRefineOpen(false)}
        onRefine={handleRefine}
        isRefining={isMutating}
      />

      {/* 链式配置 */}
      <Drawer
        title="🔗 技能链式配置"
        open={chainOpen}
        onClose={() => setChainOpen(false)}
        width={480}
        destroyOnHidden
      >
        <SkillChain skills={skills} chainNodes={chainNodes} onChange={handleChainChange} />
      </Drawer>
    </div>
  )
}
