/**
 * TranslatePanel 组件测试
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { TranslatePanel } from '../components/translate-panel'

// Mock the useTranslate hook
const mockSetSourceText = vi.fn()
const mockSetSourceLang = vi.fn()
const mockSetTargetLang = vi.fn()
const mockSetMode = vi.fn()
const mockDoTranslate = vi.fn()
const mockSwapLanguages = vi.fn()
const mockLoadHistory = vi.fn()
const mockHandleFavorite = vi.fn()
const mockClearInput = vi.fn()

vi.mock('../hooks/use-translate', () => ({
  useTranslate: () => ({
    sourceText: '',
    setSourceText: mockSetSourceText,
    sourceLang: 'auto',
    setSourceLang: mockSetSourceLang,
    targetLang: 'en',
    setTargetLang: mockSetTargetLang,
    mode: 'general' as const,
    setMode: mockSetMode,
    isTranslating: false,
    result: null,
    history: [],
    isLoadingHistory: false,
    languages: [
      { code: 'auto', name: '自动检测', nameEn: 'Auto Detect' },
      { code: 'zh', name: '中文', nameEn: 'Chinese' },
      { code: 'en', name: '英语', nameEn: 'English' }
    ],
    detectedLang: null,
    doTranslate: mockDoTranslate,
    swapLanguages: mockSwapLanguages,
    loadHistory: mockLoadHistory,
    handleFavorite: mockHandleFavorite,
    clearInput: mockClearInput
  })
}))

// Mock child components
vi.mock('../components/language-selector', () => ({
  LanguageSelector: () => <div data-testid="language-selector" />
}))

vi.mock('../components/translate-input', () => ({
  TranslateInput: ({
    onTranslate,
    onClear
  }: {
    onTranslate: () => void
    onClear: () => void
  }) => (
    <div data-testid="translate-input">
      <button onClick={onTranslate}>Translate</button>
      <button onClick={onClear}>Clear</button>
    </div>
  )
}))

vi.mock('../components/translate-output', () => ({
  TranslateOutput: () => <div data-testid="translate-output" />
}))

vi.mock('../components/translate-history', () => ({
  TranslateHistory: () => <div data-testid="translate-history" />
}))

describe('TranslatePanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the translate panel with title', () => {
    render(<TranslatePanel />)
    expect(screen.getByText('🌐 翻译')).toBeDefined()
  })

  it('renders language selector', () => {
    render(<TranslatePanel />)
    expect(screen.getByTestId('language-selector')).toBeDefined()
  })

  it('renders translate input', () => {
    render(<TranslatePanel />)
    expect(screen.getByTestId('translate-input')).toBeDefined()
  })

  it('renders translate output', () => {
    render(<TranslatePanel />)
    expect(screen.getByTestId('translate-output')).toBeDefined()
  })

  it('renders translate history', () => {
    render(<TranslatePanel />)
    expect(screen.getByTestId('translate-history')).toBeDefined()
  })

  it('triggers translate when button clicked', () => {
    render(<TranslatePanel />)
    fireEvent.click(screen.getByText('Translate'))
    expect(mockDoTranslate).toHaveBeenCalled()
  })

  it('triggers clear when button clicked', () => {
    render(<TranslatePanel />)
    fireEvent.click(screen.getByText('Clear'))
    expect(mockClearInput).toHaveBeenCalled()
  })

  it('shows keyboard shortcut hint', () => {
    render(<TranslatePanel />)
    expect(screen.getByText('Ctrl+Enter 翻译')).toBeDefined()
  })
})
