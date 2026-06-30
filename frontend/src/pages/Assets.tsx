import { useEffect, useState, useCallback } from 'react'
import { Space, Select, Row, Col, Statistic, Card, Button } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'

import ViewSelector from '../components/layout/ViewSelector'
import PortfolioPie from '../components/assets/PortfolioPie'
import TrendChart from '../components/assets/TrendChart'
import { portfolioSummary, monthlyTrend } from '../api/assets'
import type { ViewMode, PortfolioItem, MonthlyTrend } from '../types'

interface Props {
  viewMode: ViewMode
  onViewChange: (v: ViewMode) => void
  user1Name: string
  user2Name: string
}

const YEARS = Array.from({ length: 3 }, (_, i) => dayjs().year() - i)

export default function Assets({ viewMode, onViewChange, user1Name, user2Name }: Props) {
  const [loading, setLoading] = useState(false)
  const [year, setYear] = useState(dayjs().year())
  const [month, setMonth] = useState(dayjs().month() + 1)
  const [portfolio, setPortfolio] = useState<PortfolioItem[]>([])
  const [totalKrw, setTotalKrw] = useState(0)
  const [trend, setTrend] = useState<MonthlyTrend[]>([])

  const userParam = viewMode === 'user1' ? user1Name : viewMode === 'user2' ? user2Name : undefined

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const [portRes, trendRes] = await Promise.all([
        portfolioSummary({ user: userParam, year, month }),
        monthlyTrend({ user: userParam, year }),
      ])
      setPortfolio(portRes.data)
      setTotalKrw(portRes.total_krw)
      setTrend(trendRes.data)
    } finally {
      setLoading(false)
    }
  }, [userParam, year, month])

  useEffect(() => { fetchData() }, [fetchData])

  const cashKrw = portfolio.filter((p) => p.asset_type === '현금').reduce((s, p) => s + p.balance_krw, 0)
  const cryptoKrw = portfolio.filter((p) => p.asset_type !== '현금' && p.asset_type !== '주식').reduce((s, p) => s + p.balance_krw, 0)
  const stockKrw = portfolio.filter((p) => p.asset_type === '주식').reduce((s, p) => s + p.balance_krw, 0)

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="middle">
      {/* 뷰 전환 + 필터 */}
      <Row gutter={[16, 8]} align="middle">
        <Col>
          <ViewSelector value={viewMode} onChange={onViewChange} user1Name={user1Name} user2Name={user2Name} />
        </Col>
        <Col>
          <Select
            value={year}
            onChange={setYear}
            style={{ width: 90 }}
            options={YEARS.map((y) => ({ label: `${y}년`, value: y }))}
          />
        </Col>
        <Col>
          <Select
            value={month}
            onChange={setMonth}
            style={{ width: 80 }}
            options={Array.from({ length: 12 }, (_, i) => ({ label: `${i + 1}월`, value: i + 1 }))}
          />
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={fetchData} loading={loading}>새로고침</Button>
        </Col>
      </Row>

      {/* 요약 */}
      <Row gutter={16}>
        <Col span={6}>
          <Card size="small">
            <Statistic title="총자산" value={totalKrw} suffix="원"
              formatter={(v) => Number(v).toLocaleString()} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="현금성 자산" value={cashKrw} suffix="원"
              formatter={(v) => Number(v).toLocaleString()} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="가상자산" value={cryptoKrw} suffix="원"
              formatter={(v) => Number(v).toLocaleString()} />
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small">
            <Statistic title="주식/증권" value={stockKrw} suffix="원"
              formatter={(v) => Number(v).toLocaleString()} />
          </Card>
        </Col>
      </Row>

      {/* 차트 */}
      <Row gutter={16}>
        <Col span={8}>
          <PortfolioPie data={portfolio} totalKrw={totalKrw} />
        </Col>
        <Col span={16}>
          <TrendChart data={trend} title={`${year}년 월별 자산 추이`} />
        </Col>
      </Row>
    </Space>
  )
}
