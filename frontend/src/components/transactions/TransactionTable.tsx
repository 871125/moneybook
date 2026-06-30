import { Table, Tag, Select, Space, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { Transaction } from '../../types'
import { updateTags } from '../../api/transactions'

const { Text } = Typography

const PERSON_OPTIONS = ['본인', '배우자', '자녀', '공동']
const CATEGORY_OPTIONS = [
  '식비', '주거비', '차량유지비', '육아용품', '교육/육아',
  '의료/건강', '문화/여가', '통신', '보험', '저축/투자', '기타',
]

interface Props {
  data: Transaction[]
  loading: boolean
  onTagUpdated: () => void
}

export default function TransactionTable({ data, loading, onTagUpdated }: Props) {
  const handleTagChange = async (index: number, field: 'tag_person' | 'tag_category', value: string) => {
    await updateTags(
      index,
      field === 'tag_person' ? value : undefined,
      field === 'tag_category' ? value : undefined,
    )
    onTagUpdated()
  }

  const columns: ColumnsType<Transaction & { _index: number }> = [
    { title: '날짜', dataIndex: 'date', width: 110, sorter: (a, b) => a.date.localeCompare(b.date) },
    { title: '사용자', dataIndex: 'user', width: 80 },
    { title: '기관', dataIndex: 'institution', width: 110 },
    {
      title: '구분',
      dataIndex: 'type',
      width: 70,
      render: (t) => {
        const color = t === '입금' ? 'green' : t === '취소' ? 'default' : 'red'
        return <Tag color={color}>{t}</Tag>
      },
    },
    {
      title: '금액',
      dataIndex: 'amount',
      width: 120,
      align: 'right',
      sorter: (a, b) => Number(a.amount) - Number(b.amount),
      render: (v) => <Text>{Number(v).toLocaleString()}원</Text>,
    },
    { title: '내용', dataIndex: 'description', ellipsis: true },
    {
      title: '대분류(사람)',
      dataIndex: 'tag_person',
      width: 130,
      render: (v, row) => (
        <Select
          size="small"
          value={v || undefined}
          placeholder="선택"
          style={{ width: 110 }}
          options={PERSON_OPTIONS.map((o) => ({ label: o, value: o }))}
          onChange={(val) => handleTagChange(row._index, 'tag_person', val)}
          allowClear
        />
      ),
    },
    {
      title: '중분류(카테고리)',
      dataIndex: 'tag_category',
      width: 160,
      render: (v, row) => (
        <Select
          size="small"
          value={v || undefined}
          placeholder="선택"
          style={{ width: 140 }}
          options={CATEGORY_OPTIONS.map((o) => ({ label: o, value: o }))}
          onChange={(val) => handleTagChange(row._index, 'tag_category', val)}
          allowClear
        />
      ),
    },
  ]

  const dataWithIndex = data.map((row, i) => ({ ...row, _index: i, key: i }))

  return (
    <Table
      columns={columns}
      dataSource={dataWithIndex}
      loading={loading}
      scroll={{ x: 900 }}
      pagination={{ pageSize: 50, showSizeChanger: true, showTotal: (t) => `총 ${t}건` }}
      size="small"
    />
  )
}
