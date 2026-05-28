import { useCallback } from 'react'
import CodeMirror from '@uiw/react-codemirror'
import { javascript } from '@codemirror/lang-javascript'
import { python } from '@codemirror/lang-python'
import { html } from '@codemirror/lang-html'
import { css } from '@codemirror/lang-css'
import { oneDark } from '@codemirror/theme-one-dark'
import { useTheme } from '@/hooks/use-theme'
import styles from './snippets-panel.module.css'

/** 语言扩展映射 */
const languageExtensions: Record<string, () => ReturnType<typeof javascript>> = {
  javascript: () => javascript({ jsx: true }),
  typescript: () => javascript({ jsx: true, typescript: true }),
  python: () => python(),
  html: () => html(),
  css: () => css()
}

function getLanguageExtension(lang: string) {
  const ext = languageExtensions[lang]
  return ext ? [ext()] : []
}

interface SnippetEditorProps {
  value: string
  onChange: (value: string) => void
  language?: string
  readOnly?: boolean
  height?: string
}

export function SnippetEditor({
  value,
  onChange,
  language = 'typescript',
  readOnly = false,
  height = '100%'
}: SnippetEditorProps) {
  const { isDark } = useTheme()

  const handleChange = useCallback(
    (val: string) => {
      onChange(val)
    },
    [onChange]
  )

  return (
    <div className={styles.editorWrapper}>
      <CodeMirror
        value={value}
        height={height}
        extensions={getLanguageExtension(language)}
        theme={isDark ? oneDark : 'light'}
        onChange={handleChange}
        readOnly={readOnly}
        basicSetup={{
          lineNumbers: true,
          highlightActiveLineGutter: true,
          highlightActiveLine: true,
          foldGutter: true,
          autocompletion: true,
          bracketMatching: true,
          closeBrackets: true,
          indentOnInput: true
        }}
      />
    </div>
  )
}
