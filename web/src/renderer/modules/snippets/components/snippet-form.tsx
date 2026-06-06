import { useEffect } from 'react'
import { Form, Input, Select } from 'antd'
import { useForm, Controller } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { SnippetEditor } from './snippet-editor'
import { LANGUAGE_OPTIONS, type Snippet, type SnippetFormData } from '../types/snippets'
import styles from './snippets-panel.module.css'

const snippetSchema = z.object({
  title: z.string().min(1, '请输入标题').max(100, '标题不超过 100 字'),
  content: z.string().min(1, '请输入代码内容'),
  language: z.string().min(1, '请选择语言'),
  tags: z.array(z.string()).default([]),
})

type SnippetFormValues = z.infer<typeof snippetSchema>

interface SnippetFormProps {
  snippet?: Snippet | null
  onSubmit: (data: SnippetFormData) => void
  loading?: boolean
}

export function SnippetForm({ snippet, onSubmit, loading }: SnippetFormProps) {
  const {
    control,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<SnippetFormValues>({
    resolver: zodResolver(snippetSchema),
    defaultValues: {
      title: '',
      content: '',
      language: 'typescript',
      tags: [],
    },
  })

  const content = watch('content')
  const language = watch('language')

  // 编辑模式：填充表单
  useEffect(() => {
    if (snippet) {
      reset({
        title: snippet.title,
        content: snippet.content,
        language: snippet.language,
        tags: snippet.tags,
      })
    } else {
      reset({
        title: '',
        content: '',
        language: 'typescript',
        tags: [],
      })
    }
  }, [snippet, reset])

  const handleFormSubmit = (values: SnippetFormValues) => {
    onSubmit({
      title: values.title,
      content: values.content,
      language: values.language,
      tags: values.tags,
    })
  }

  return (
    <Form
      id="snippet-form"
      layout="vertical"
      onFinish={handleSubmit(handleFormSubmit)}
      className={styles.snippetForm}
      disabled={loading}
    >
      <Form.Item
        label="标题"
        required
        validateStatus={errors.title ? 'error' : undefined}
        help={errors.title?.message}
      >
        <Controller
          name="title"
          control={control}
          render={({ field }) => <Input {...field} placeholder="给片段起个名字" maxLength={100} />}
        />
      </Form.Item>

      <Form.Item label="语言" required>
        <Controller
          name="language"
          control={control}
          render={({ field }) => (
            <Select
              {...field}
              options={LANGUAGE_OPTIONS}
              placeholder="选择语言"
              showSearch
              style={{ width: '100%' }}
            />
          )}
        />
      </Form.Item>

      <Form.Item label="标签">
        <Controller
          name="tags"
          control={control}
          render={({ field }) => (
            <Select
              {...field}
              mode="tags"
              placeholder="输入标签后回车"
              style={{ width: '100%' }}
              maxCount={10}
            />
          )}
        />
      </Form.Item>

      <Form.Item
        label="代码内容"
        required
        validateStatus={errors.content ? 'error' : undefined}
        help={errors.content?.message}
        className={styles.editorFormItem}
      >
        <div className={styles.editorContainer}>
          <SnippetEditor
            value={content}
            onChange={(val) => setValue('content', val, { shouldValidate: true })}
            language={language}
            height="400px"
          />
        </div>
      </Form.Item>
    </Form>
  )
}
