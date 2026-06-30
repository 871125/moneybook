import { useEffect, useState, useCallback } from 'react'
import { Space, DatePicker, Select, Button, Row, Col, Statistic, Card } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import dayjs, { Dayjs } from 'dayjs'

import ViewSelector from '../components/layout/ViewSelector'
import TransactionTable from '../components/transactions/TransactionTable'
import CategoryChart from '../components/transactions/CategoryChart'
import { listTransactions, categorySummary } from '../api/transactions'
import type { ViewMode, Transaction, CategorySummary } from '../types'

const { RangePicker } = DatePicker

interface Props {
  viewMode: ViewMode
  onViewChange: (v: ViewMode) => void
  user1Name: string
  user2Name: string
}

export default function Transactions({ viewMode, onViewChange, user1Name, user2Name }: Props) {
  const [loading, setLoading] = useState(false)
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [categories, setCategories] = useState<CategorySummary[]>([])
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs]>([
    dayjs().startOf('month'),
    dayjs().endOf('month'),
  ])
  const [institutionFilter, setInstitutionFilter] = useState<string | undefined>()

  const userParam = viewMode === 'user1' ? user1Name : viewMode === 'user2' ? user2Name : undefined

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const params = {
        user: userParam,
        date_from: dateRange[0].format('YYYY-MM-DD'),
        date_to: dateRange[1].format('YYYY-MM-DD'),
        institution: institutionFilter,
        limit: 500,
      }
      const [txRes, catRes] = await Promise.all([
        listTransactions(params),
        categorySummary({ user: userParam, date_from: params.date_from, date_to: params.date_to }),
      ])
      setTransactions(txRes.data)
      setCategories(catRes.data)
    } finally {
      setLoading(false)
    }
  }, [userParam, dateRange, institutionFilter])

  useEffect(() => { fetchData() }, [fetchData])

  const totalExpense = transactions
    .filter((t) => t.type === '출금' || t.type === '승인')
    .reduce((s, t) => s + Number(t.amount), 0)
  const totalIncome = transactions
    .filter((t) => t.type === '입금')
    .reduce((s, t) => s + Number(t.amount), 0)

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      {/* 뷰 전환 + 필터 */}
      <Row gutter={[16, 8]} align="middle">
        <Col>
          <ViewSelector value={viewMode} onChange={onViewChange} user1Name={user1Name} user2Name={user2Name} />
        </Col>
        <Col>
          <RangePicker
            value={dateRange}
            onChange={(v) => v && setDateRange(v as [Dayjs, Dayjs])}
          />
        </Col>
        <Col>
          <Select
            placeholder="기관 필터"
            allowClear
            style={{ width: 140 }}
            value={institutionFilter}
            onChange={setInstitutionFilter}
            options={[
              '우리은행', '카카오뱅크', '새마을금고', '하나은행',
              '우리카드', '하나카드', '신한카드',
              '삼성증권', '미래에셋', '메리츠', 'NH',
            ].map((v) => ({ label: v, value: v }))}
          />
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>새로고침</Button>
        </Col>
      </Row>

      {/* 요약 통계 */}
      <Row gutter={16}>
        <Col span={6}>
          <Card size="small">
            <Statistic title="총 지출" value={totalExpense} suffix="원" valueStyle={{ color: '#cf1322' }}
              formatter={(v) => Number(v).toLocaleString()} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="총 수입" value={totalIncome} suffix="원" valueStyle={{ color: '#3f8600' }}
              formatter={(v) => Number(v).toLocaleString()} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="순수지" value={totalIncome - totalExpense} suffix="원"
              valueStyle={{ color: totalIncome - totalExpense >= 0 ? '#3f8600' : '#cf1322' }}
              formatter={(v) => Number(v).toLocaleString()} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="거래 건수" value={transactions.length} suffix="건" />
          </Card>
        </Col>
      </Row>

      {/* 카테고리 차트 + 테이블 */}
      <Row gutter={16}>
        <Col span={6}>
          <CategoryChart data={categories} />
        </Col>
        <Col span={18}>
          <TransactionTable data={transactions} loading={loading} onTagUpdated={fetchData} />
        </Col>
      </Row>
    </Space>
  )
}
