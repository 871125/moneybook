import { Card } from 'antd'
import type { MonthlyTrend } from '../../types'

interface Props {
  data: MonthlyTrend[]
  title?: string
}

export default function TrendChart({ data, title = '월별 총자산 추이' }: Props) {
  if (data.length === 0) return <Card title={title} size="small"><p style={{ color: '#999' }}>데이터 없음</p></Card>

  const max = Math.max(...data.map((d) => d.total_krw), 1)
  const chartH = 120
  const chartW = 300
  const padL = 10
  const padB = 24

  const points = data.map((d, i) => ({
    x: padL + (i / Math.max(data.length - 1, 1)) * (chartW - padL * 2),
    y: chartH - padB - ((d.total_krw / max) * (chartH - padB - 8)),
    ...d,
  }))

  const polyline = points.map((p) => `${p.x},${p.y}`).join(' ')

  return (
    <Card title={title} size="small">
      <svg viewBox={`0 0 ${chartW} ${chartH}`} style={{ width: '100%' }}>
        <polyline points={polyline} fill="none" stroke="#1677ff" strokeWidth={2} />
        {points.map((p, i) => (
          <g key={i}>
            <circle cx={p.x} cy={p.y} r={3} fill="#1677ff" />
            <text x={p.x} y={chartH - 6} textAnchor="middle" fontSize={9} fill="#888">
              {p.month.slice(5)}월
            </text>
            <text x={p.x} y={p.y - 6} textAnchor="middle" fontSize={8} fill="#333">
              {(p.total_krw / 10000).toFixed(0)}만
            </text>
          </g>
        ))}
      </svg>
    </Card>
  )
}
