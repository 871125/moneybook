import client from './client'
import type { MonthlyAsset, PortfolioItem, MonthlyTrend } from '../types'

interface AssetParams {
  user?: string
  year?: number
  month?: number
  institution?: string
  asset_type?: string
}

export async function listAssets(params: AssetParams = {}): Promise<{ total: number; data: MonthlyAsset[] }> {
  const { data } = await client.get('/assets/', { params })
  return data
}

export async function portfolioSummary(params: { user?: string; year?: number; month?: number }): Promise<{ total_krw: number; data: PortfolioItem[] }> {
  const { data } = await client.get('/assets/summary/portfolio', { params })
  return data
}

export async function monthlyTrend(params: { user?: string; year?: number }): Promise<{ data: MonthlyTrend[] }> {
  const { data } = await client.get('/assets/summary/monthly-trend', { params })
  return data
}
