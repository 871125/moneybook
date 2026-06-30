import { Card } from 'antd'
import type { CategorySummary } from '../../types'

interface Props {
  data: CategorySummary[]
  title?: string
}

export default function CategoryChart({ data, title = '카테고리별 지출' }: Props) {
  const max = Math.max(...data.map((d) => d.total), 1)

  return (
    <Card title={title} size="small">
      {data.length === 0 && <p style={{ color: '#999' }}>데이터 없음</p>}
      {data.map((item) => (
        <div key={item.category} style={{ marginBottom: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
            <span>{item.category}</span>
            <span>{item.total.toLocaleString()}원</span>
          </div>
          <div style={{ background: '#f0f0f0', borderRadius: 4, height: 8 }}>
            <div
              style={{
                width: `${(item.total / max) * 100}%`,
                background: '#1677ff',
                height: 8,
                borderRadius: 4,
                transition: 'width 0.4s',
              }}
            />
          </div>
        </div>
      ))}
    </Card>
  )
}
