import client from './client'
import type { Transaction, CategorySummary, PersonSummary } from '../types'

interface ListParams {
  user?: string
  date_from?: string
  date_to?: string
  tag_person?: string
  tag_category?: string
  institution?: string
  skip?: number
  limit?: number
}

export async function listTransactions(params: ListParams = {}): Promise<{ total: number; data: Transaction[] }> {
  const { data } = await client.get('/transactions/', { params })
  return data
}

export async function updateTags(index: number, tag_person?: string, tag_category?: string) {
  const { data } = await client.patch(`/transactions/${index}`, { tag_person, tag_category })
  return data
}

export async function categorySummary(params: { user?: string; date_from?: string; date_to?: string }): Promise<{ data: CategorySummary[] }> {
  const { data } = await client.get('/transactions/summary/category', { params })
  return data
}

export async function personSummary(params: { user?: string; date_from?: string; date_to?: string }): Promise<{ data: PersonSummary[] }> {
  const { data } = await client.get('/transactions/summary/person', { params })
  return data
}
