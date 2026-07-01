import { Segmented } from 'antd'
import type { ViewMode } from '../../types'

interface Props {
  value: ViewMode
  onChange: (v: ViewMode) => void
  user1Name?: string
  user2Name?: string
  user3Name?: string
}

export default function ViewSelector({ value, onChange, user1Name = 'User1', user2Name = 'User2', user3Name = 'User3' }: Props) {
  return (
    <Segmented
      value={value}
      onChange={(v) => onChange(v as ViewMode)}
      options={[
        { label: user1Name, value: 'user1' },
        { label: user2Name, value: 'user2' },
        { label: user3Name, value: 'user3' },
        { label: '통합', value: 'combined' },
      ]}
      size="large"
    />
  )
}
