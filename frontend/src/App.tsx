import { useState } from 'react'
import { ConfigProvider, Layout, Menu, Typography } from 'antd'
import { WalletOutlined, BarChartOutlined } from '@ant-design/icons'
import koKR from 'antd/locale/ko_KR'
import dayjs from 'dayjs'
import 'dayjs/locale/ko'

import Transactions from './pages/Transactions'
import Assets from './pages/Assets'
import type { ViewMode } from './types'

dayjs.locale('ko')

const { Header, Content } = Layout
const { Title } = Typography

const USER1_NAME = import.meta.env.VITE_USER1_NAME ?? 'User1'
const USER2_NAME = import.meta.env.VITE_USER2_NAME ?? 'User2'

type PageKey = 'transactions' | 'assets'

export default function App() {
  const [page, setPage] = useState<PageKey>('transactions')
  const [viewMode, setViewMode] = useState<ViewMode>('combined')

  return (
    <ConfigProvider locale={koKR}>
      <Layout style={{ minHeight: '100vh' }}>
        <Header style={{ display: 'flex', alignItems: 'center', gap: 24, padding: '0 24px' }}>
          <Title level={4} style={{ color: '#fff', margin: 0, whiteSpace: 'nowrap' }}>
            가계부 대시보드
          </Title>
          <Menu
            theme="dark"
            mode="horizontal"
            selectedKeys={[page]}
            onClick={({ key }) => setPage(key as PageKey)}
            items={[
              { key: 'transactions', icon: <WalletOutlined />, label: '가계부' },
              { key: 'assets', icon: <BarChartOutlined />, label: '자산 현황' },
            ]}
            style={{ flex: 1 }}
          />
        </Header>
        <Content style={{ padding: 24 }}>
          {page === 'transactions' ? (
            <Transactions
              viewMode={viewMode}
              onViewChange={setViewMode}
              user1Name={USER1_NAME}
              user2Name={USER2_NAME}
            />
          ) : (
            <Assets
              viewMode={viewMode}
              onViewChange={setViewMode}
              user1Name={USER1_NAME}
              user2Name={USER2_NAME}
            />
          )}
        </Content>
      </Layout>
    </ConfigProvider>
  )
}
