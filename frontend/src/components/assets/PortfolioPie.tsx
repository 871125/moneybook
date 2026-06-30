import { Card } from 'antd'
import type { PortfolioItem } from '../../types'

const COLORS = ['#1677ff', '#52c41a', '#faad14', '#f5222d', '#722ed1', '#13c2c2', '#eb2f96', '#fa8c16']

interface Props {
  data: PortfolioItem[]
  totalKrw: number
}

export default function PortfolioPie({ data, totalKrw }: Props) {
  const radius = 80
  const cx = 100
  const cy = 100
  let cumulative = 0

  const slices = data.map((item, i) => {
    const ratio = totalKrw > 0 ? item.balance_krw / totalKrw : 0
    const startAngle = cumulative * 2 * Math.PI - Math.PI / 2
    cumulative += ratio
    const endAngle = cumulative * 2 * Math.PI - Math.PI / 2
    const x1 = cx + radius * Math.cos(startAngle)
    const y1 = cy + radius * Math.sin(startAngle)
    const x2 = cx + radius * Math.cos(endAngle)
    const y2 = cy + radius * Math.sin(endAngle)
    const largeArc = ratio > 0.5 ? 1 : 0
    return { ...item, x1, y1, x2, y2, largeArc, color: COLORS[i % COLORS.length], ratio }
  })

  return (
    <Card title="자산 포트폴리오" size="small">
      {data.length === 0 ? (
        <p style={{ color: '#999' }}>데이터 없음</p>
      ) : (
        <>
          <svg viewBox="0 0 200 200" style={{ width: '100%', maxWidth: 200 }}>
            {slices.map((s, i) => (
              <path
                key={i}
                d={`M${cx},${cy} L${s.x1},${s.y1} A${radius},${radius} 0 ${s.largeArc},1 ${s.x2},${s.y2} Z`}
                fill={s.color}
                stroke="#fff"
                strokeWidth={1}
              />
            ))}
            <circle cx={cx} cy={cy} r={40} fill="#fff" />
            <text x={cx} y={cy - 6} textAnchor="middle" fontSize={9} fill="#555">총자산</text>
            <text x={cx} y={cy + 8} textAnchor="middle" fontSize={8} fill="#333">
              {(totalKrw / 10000).toLocaleString()}만원
            </text>
          </svg>
          <div style={{ marginTop: 8 }}>
            {slices.map((s, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                <span>
                  <span style={{ display: 'inline-block', width: 10, height: 10, background: s.color, borderRadius: 2, marginRight: 4 }} />
                  {s.asset_type}
                </span>
                <span>{s.ratio.toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </>
      )}
    </Card>
  )
}
