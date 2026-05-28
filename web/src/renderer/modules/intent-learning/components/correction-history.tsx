import { Table, Tag } from 'antd'
import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-cn'
import { useIntentCorrections } from '../hooks/use-intent-learning'
import type { IntentCorrection } from '../types/intent-learning'

dayjs.extend(relativeTime)
dayjs.locale('zh-cn')

const columns = [
  {
    title: '原始意图',
    dataIndex: 'originalIntent',
    key: 'originalIntent',
  },
  {
    title: '纠正为',
    dataIndex: 'correctModule',
    key: 'correctModule',
    render: (module: string) => <Tag color="blue">{module}</Tag>,
  },
  {
    title: '时间',
    dataIndex: 'createdAt',
    key: 'createdAt',
    render: (time: string) => dayjs(time).fromNow(),
  },
]

export default function CorrectionHistory() {
  const { data: corrections = [], isLoading } = useIntentCorrections()

  return (
    <Table<IntentCorrection>
      columns={columns}
      dataSource={corrections}
      rowKey="id"
      loading={isLoading}
      pagination={{ pageSize: 10 }}
      size="small"
    />
  )
}
