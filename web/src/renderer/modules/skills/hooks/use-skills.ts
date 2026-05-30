/** 技能管理 hooks（TanStack Query） */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useCallback, useMemo, useState } from 'react'
import type { Skill, InstallSkillInput, RefineResult } from '../types/skills'
import { fetchSkills, installSkill, toggleSkill, refineSkill } from '../services/skills-api'

const QUERY_KEY = ['skills']

export interface UseSkillsReturn {
  /** 技能列表 */
  skills: Skill[]
  /** 已启用的技能 */
  enabledSkills: Skill[]
  /** 加载中 */
  isLoading: boolean
  /** 错误 */
  error: Error | null
  /** 搜索关键词 */
  keyword: string
  setKeyword: (kw: string) => void
  /** 筛选后的技能列表 */
  filteredSkills: Skill[]
  /** 安装技能 */
  installSkillMut: (input: InstallSkillInput) => Promise<Skill>
  /** 切换技能启用/禁用 */
  toggleSkillMut: (id: string, enabled: boolean) => Promise<Skill>
  /** 炼化技能 */
  refineSkillMut: (id: string, prompt?: string) => Promise<RefineResult>
  /** 是否有正在提交的操作 */
  isMutating: boolean
}

export function useSkills(): UseSkillsReturn {
  const queryClient = useQueryClient()
  const [keyword, setKeyword] = useState('')

  const {
    data: skillsResult,
    isLoading,
    error,
  } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: fetchSkills,
  })

  const skills: Skill[] = skillsResult?.data ?? []

  const installMut = useMutation({
    mutationFn: (input: InstallSkillInput) => installSkill(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY })
    },
  })

  const toggleMut = useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) => toggleSkill(id, enabled),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: QUERY_KEY })
    },
  })

  const refineMut = useMutation({
    mutationFn: ({ id, prompt }: { id: string; prompt?: string }) => refineSkill(id, prompt),
  })

  const installSkillMut = useCallback(
    (input: InstallSkillInput) => installMut.mutateAsync(input),
    [installMut]
  )

  const toggleSkillMut = useCallback(
    (id: string, enabled: boolean) => toggleMut.mutateAsync({ id, enabled }),
    [toggleMut]
  )

  const refineSkillMut = useCallback(
    (id: string, prompt?: string) => refineMut.mutateAsync({ id, prompt }),
    [refineMut]
  )

  const enabledSkills = useMemo(() => skills.filter((s) => s.enabled), [skills])

  const filteredSkills = useMemo(() => {
    if (!keyword) return skills
    const kw = keyword.toLowerCase()
    return skills.filter(
      (s) =>
        s.name.toLowerCase().includes(kw) ||
        s.description.toLowerCase().includes(kw) ||
        s.triggerWords.some((t) => t.toLowerCase().includes(kw))
    )
  }, [skills, keyword])

  const isMutating = installMut.isPending || toggleMut.isPending || refineMut.isPending

  return {
    skills,
    enabledSkills,
    isLoading,
    error: error as Error | null,
    keyword,
    setKeyword,
    filteredSkills,
    installSkillMut,
    toggleSkillMut,
    refineSkillMut,
    isMutating,
  }
}
