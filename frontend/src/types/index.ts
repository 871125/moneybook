export type ViewMode = 'user1' | 'user2' | 'user3' | 'combined'

export interface Transaction {
  date: string
  user: string
  institution: string
  type: string
  amount: number
  description: string
  tag_person: string
  tag_category: string
}

export interface MonthlyAsset {
  snapshot_date: string
  user: string
  institution: string
  asset_type: string
  balance_krw: number
}

export interface CategorySummary {
  category: string
  total: number
}

export interface PersonSummary {
  person: string
  total: number
}

export interface PortfolioItem {
  asset_type: string
  balance_krw: number
  ratio: number
}

export interface MonthlyTrend {
  month: string
  total_krw: number
}
