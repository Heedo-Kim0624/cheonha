import React, { useCallback, useMemo, useState } from 'react'
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { NativeStackNavigationProp } from '@react-navigation/native-stack'
import { useFocusEffect, useNavigation } from '@react-navigation/native'

import { colors, radius, spacing } from '../theme'
import { api, RequestHistoryResponse } from '../services/api'
import { RootStackParamList } from '../navigation/types'

type Nav = NativeStackNavigationProp<RootStackParamList, 'RequestHistory'>
type HistoryTab = 'subscription' | 'return' | 'as'

const TAB_ITEMS: Array<{ key: HistoryTab; label: string }> = [
  { key: 'subscription', label: '구독 요청' },
  { key: 'return', label: '구독 반납' },
  { key: 'as', label: 'A/S 요청' },
]

const STATUS_FILTERS: Record<HistoryTab, Array<{ key: string; label: string }>> = {
  subscription: [
    { key: 'ALL', label: '전체' },
    { key: 'REQUESTED', label: '대기' },
    { key: 'APPROVED', label: '승인' },
    { key: 'REJECTED', label: '반려' },
    { key: 'COMPLETED', label: '완료' },
  ],
  return: [
    { key: 'ALL', label: '전체' },
    { key: 'REQUESTED', label: '대기' },
    { key: 'CONFIRMED', label: '확정' },
    { key: 'NEEDS_ADJUST', label: '조정' },
    { key: 'COMPLETED', label: '완료' },
  ],
  as: [
    { key: 'ALL', label: '전체' },
    { key: 'REQUESTED', label: '접수' },
    { key: 'REPAIRING', label: '수리/대기' },
    { key: 'OPERATING', label: '운영중' },
    { key: 'COMPLETED', label: '완료' },
  ],
}

const EMPTY_HISTORY: RequestHistoryResponse = {
  subscription_requests: [],
  return_requests: [],
  as_requests: [],
}
const REQUEST_HISTORY_ERROR_TITLE = '\uC694\uCCAD \uC774\uB825\uC744 \uBD88\uB7EC\uC624\uC9C0 \uBABB\uD588\uC2B5\uB2C8\uB2E4.'
const RETRY_LABEL = '\uB2E4\uC2DC \uC2DC\uB3C4'

function formatDateTime(value?: string | null) {
  if (!value) return '-'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleString('ko-KR', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function statusStyle(status: string) {
  if (['REJECTED', 'NEEDS_ADJUST'].includes(status)) return styles.badgeDanger
  if (['APPROVED', 'CONFIRMED', 'OPERATING', 'COMPLETED'].includes(status)) return styles.badgeSuccess
  return styles.badgePending
}

function CountBadge({ value }: { value: number }) {
  return (
    <View style={styles.countBadge}>
      <Text style={styles.countBadgeText}>{value}</Text>
    </View>
  )
}

export default function RequestHistoryScreen() {
  const nav = useNavigation<Nav>()
  const [activeTab, setActiveTab] = useState<HistoryTab>('subscription')
  const [statusFilter, setStatusFilter] = useState('ALL')
  const [refreshing, setRefreshing] = useState(false)
  const [loading, setLoading] = useState(true)
  const [history, setHistory] = useState<RequestHistoryResponse | null>(null)
  const [errorMessage, setErrorMessage] = useState('')

  const load = useCallback(async (showSpinner = false) => {
    if (showSpinner) {
      setLoading(true)
    }
    setRefreshing(!showSpinner)
    setErrorMessage('')
    try {
      const { data, error } = await api.getRequestHistory()
      if (error) {
        setErrorMessage(error)
        setHistory((current) => current || EMPTY_HISTORY)
        return
      }
      setHistory(data || EMPTY_HISTORY)
    } catch (error: any) {
      setErrorMessage(error?.message || REQUEST_HISTORY_ERROR_TITLE)
      setHistory((current) => current || EMPTY_HISTORY)
    } finally {
      setRefreshing(false)
      setLoading(false)
    }
  }, [])

  useFocusEffect(
    useCallback(() => {
      load(true)
    }, [load]),
  )

  const subscriptionRows = useMemo(() => {
    const rows = history?.subscription_requests || []
    return statusFilter === 'ALL' ? rows : rows.filter((row) => row.status === statusFilter)
  }, [history, statusFilter])

  const returnRows = useMemo(() => {
    const rows = history?.return_requests || []
    return statusFilter === 'ALL' ? rows : rows.filter((row) => row.status === statusFilter)
  }, [history, statusFilter])

  const asRows = useMemo(() => {
    const rows = history?.as_requests || []
    return statusFilter === 'ALL' ? rows : rows.filter((row) => row.status === statusFilter)
  }, [history, statusFilter])

  const counts = useMemo(
    () => ({
      subscription: history?.subscription_requests?.length || 0,
      return: history?.return_requests?.length || 0,
      as: history?.as_requests?.length || 0,
    }),
    [history],
  )

  const filters = STATUS_FILTERS[activeTab]

  const renderEmpty = (message: string) => (
    <View style={styles.emptyCard}>
      <Text style={styles.emptyText}>{message}</Text>
    </View>
  )

  const renderSubscriptionRows = () => {
    if (!subscriptionRows.length) return renderEmpty('조건에 맞는 구독 요청 이력이 없습니다.')
    return subscriptionRows.map((item) => (
      <View key={`subscription-${item.id}`} style={styles.itemCard}>
        <View style={styles.itemHeader}>
          <View style={styles.headerMain}>
            <Text style={styles.itemTitle}>{item.requested_date} · {item.quantity}대 요청</Text>
            <Text style={styles.itemMeta}>신청 {formatDateTime(item.created_at)} · 수정 {formatDateTime(item.updated_at)}</Text>
          </View>
          <View style={[styles.badgeBase, statusStyle(item.status)]}>
            <Text style={styles.badgeText}>{item.status_display}</Text>
          </View>
        </View>
        {item.reject_reason ? (
          <View style={styles.noteBox}>
            <Text style={styles.noteLabel}>반려 사유</Text>
            <Text style={styles.noteText}>{item.reject_reason}</Text>
          </View>
        ) : (
          <Text style={styles.inlineText}>반려 사유 없음</Text>
        )}
      </View>
    ))
  }

  const renderReturnRows = () => {
    if (!returnRows.length) return renderEmpty('조건에 맞는 반납 요청 이력이 없습니다.')
    return returnRows.map((item) => (
      <View key={`return-${item.id}`} style={styles.itemCard}>
        <View style={styles.itemHeader}>
          <View style={styles.headerMain}>
            <Text style={styles.itemTitle}>{item.vehicle_number}</Text>
            <Text style={styles.itemMeta}>
              희망일 {item.hope_date} {item.hope_time} · 사진 {item.photo_count}장
            </Text>
          </View>
          <View style={[styles.badgeBase, statusStyle(item.status)]}>
            <Text style={styles.badgeText}>{item.status_display}</Text>
          </View>
        </View>
        <Text style={styles.bodyText}>{item.reason}</Text>
        {item.confirmed_date ? (
          <Text style={styles.inlineText}>확정 일정: {item.confirmed_date} {item.confirmed_time || ''}</Text>
        ) : null}
        {item.block_reason ? (
          <View style={styles.noteBox}>
            <Text style={styles.noteLabel}>조정/반려 사유</Text>
            <Text style={styles.noteText}>{item.block_reason}</Text>
            {item.available_dates ? (
              <Text style={styles.inlineText}>가능일: {item.available_dates}</Text>
            ) : null}
          </View>
        ) : null}
        <Text style={styles.footerMeta}>신청 {formatDateTime(item.created_at)} · 수정 {formatDateTime(item.updated_at)}</Text>
      </View>
    ))
  }

  const renderASRows = () => {
    if (!asRows.length) return renderEmpty('조건에 맞는 A/S 요청 이력이 없습니다.')
    return asRows.map((item) => (
      <View key={`as-${item.id}`} style={styles.itemCard}>
        <View style={styles.itemHeader}>
          <View style={styles.headerMain}>
            <Text style={styles.itemTitle}>{item.vehicle_number}</Text>
            <Text style={styles.itemMeta}>{item.owner_name} · {item.owner_phone}</Text>
          </View>
          <View style={[styles.badgeBase, statusStyle(item.status)]}>
            <Text style={styles.badgeText}>{item.status_display}</Text>
          </View>
        </View>
        <Text style={styles.bodyText}>{item.reason}</Text>
        {item.admin_comment ? (
          <View style={styles.noteBox}>
            <Text style={styles.noteLabel}>관리자 메모</Text>
            <Text style={styles.noteText}>{item.admin_comment}</Text>
          </View>
        ) : (
          <Text style={styles.inlineText}>관리자 메모 없음</Text>
        )}
        <Text style={styles.footerMeta}>신청 {formatDateTime(item.created_at)} · 수정 {formatDateTime(item.updated_at)}</Text>
      </View>
    ))
  }

  let content = null
  if (activeTab === 'subscription') content = renderSubscriptionRows()
  if (activeTab === 'return') content = renderReturnRows()
  if (activeTab === 'as') content = renderASRows()

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => nav.goBack()}>
          <Text style={styles.back}>뒤로</Text>
        </TouchableOpacity>
        <Text style={styles.title}>요청 이력</Text>
        <TouchableOpacity onPress={() => load(false)}>
          <Text style={styles.refresh}>새로고침</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.summaryRow}>
        <View style={styles.summaryCard}>
          <Text style={styles.summaryLabel}>구독 요청</Text>
          <Text style={styles.summaryValue}>{counts.subscription}</Text>
        </View>
        <View style={styles.summaryCard}>
          <Text style={styles.summaryLabel}>구독 반납</Text>
          <Text style={styles.summaryValue}>{counts.return}</Text>
        </View>
        <View style={styles.summaryCard}>
          <Text style={styles.summaryLabel}>A/S 요청</Text>
          <Text style={styles.summaryValue}>{counts.as}</Text>
        </View>
      </View>

      <View style={styles.tabRow}>
        {TAB_ITEMS.map((item) => (
          <TouchableOpacity
            key={item.key}
            style={[styles.tabButton, activeTab === item.key && styles.tabButtonActive]}
            onPress={() => {
              setActiveTab(item.key)
              setStatusFilter('ALL')
            }}
          >
            <Text style={[styles.tabButtonText, activeTab === item.key && styles.tabButtonTextActive]}>
              {item.label}
            </Text>
            <CountBadge value={counts[item.key]} />
          </TouchableOpacity>
        ))}
      </View>

      <View style={styles.filterRow}>
        {filters.map((item) => (
          <TouchableOpacity
            key={item.key}
            style={[styles.filterChip, statusFilter === item.key && styles.filterChipActive]}
            onPress={() => setStatusFilter(item.key)}
          >
            <Text style={[styles.filterChipText, statusFilter === item.key && styles.filterChipTextActive]}>
              {item.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {loading ? (
        <View style={styles.loadingWrap}>
          <ActivityIndicator size="large" color={colors.primary} />
        </View>
      ) : (
        <ScrollView
          style={styles.scroll}
          contentContainerStyle={styles.content}
          keyboardShouldPersistTaps="handled"
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={() => load(false)} />}
        >
          {errorMessage ? (
            <View style={styles.errorCard}>
              <Text style={styles.errorTitle}>{REQUEST_HISTORY_ERROR_TITLE}</Text>
              <Text style={styles.errorText}>{errorMessage}</Text>
              <TouchableOpacity style={styles.retryButton} onPress={() => load(true)}>
                <Text style={styles.retryButtonText}>{RETRY_LABEL}</Text>
              </TouchableOpacity>
            </View>
          ) : null}
          {content}
        </ScrollView>
      )}
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg2 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
    backgroundColor: colors.bg,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  back: { color: colors.textSecondary, fontSize: 13, fontWeight: '700' },
  title: { color: colors.text, fontSize: 16, fontWeight: '700' },
  refresh: { color: colors.primary, fontSize: 13, fontWeight: '700' },
  summaryRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.lg,
  },
  summaryCard: {
    flex: 1,
    backgroundColor: colors.bg,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.md,
    gap: 6,
  },
  summaryLabel: { color: colors.textSecondary, fontSize: 12, fontWeight: '700' },
  summaryValue: { color: colors.text, fontSize: 20, fontWeight: '700' },
  tabRow: {
    flexDirection: 'row',
    gap: spacing.sm,
    padding: spacing.lg,
    paddingBottom: spacing.sm,
  },
  tabButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.xs,
    paddingVertical: 12,
    borderRadius: radius.md,
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.border,
  },
  tabButtonActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  tabButtonText: { color: colors.textSecondary, fontSize: 13, fontWeight: '700' },
  tabButtonTextActive: { color: colors.textInverse },
  countBadge: {
    minWidth: 24,
    borderRadius: 999,
    backgroundColor: 'rgba(255,255,255,0.2)',
    alignItems: 'center',
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  countBadgeText: { color: colors.textInverse, fontSize: 11, fontWeight: '700' },
  filterRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.sm,
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.sm,
  },
  filterChip: {
    borderRadius: 999,
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.border,
    paddingHorizontal: 12,
    paddingVertical: 7,
  },
  filterChipActive: {
    backgroundColor: colors.primaryLight,
    borderColor: colors.primaryLight,
  },
  filterChipText: { color: colors.textSecondary, fontSize: 12, fontWeight: '700' },
  filterChipTextActive: { color: colors.textInverse },
  loadingWrap: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  scroll: { flex: 1 },
  content: { padding: spacing.lg, gap: spacing.md, paddingBottom: 40 },
  errorCard: {
    backgroundColor: '#FEF2F2',
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: '#FECACA',
    padding: spacing.lg,
    gap: spacing.sm,
  },
  errorTitle: { color: '#991B1B', fontSize: 14, fontWeight: '800' },
  errorText: { color: '#B91C1C', fontSize: 12, lineHeight: 18 },
  retryButton: {
    alignSelf: 'flex-start',
    borderRadius: radius.md,
    backgroundColor: colors.primary,
    paddingHorizontal: 14,
    paddingVertical: 9,
  },
  retryButtonText: { color: colors.textInverse, fontSize: 12, fontWeight: '800' },
  itemCard: {
    backgroundColor: colors.bg,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
    gap: spacing.sm,
  },
  itemHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    gap: spacing.md,
  },
  headerMain: { flex: 1 },
  itemTitle: { color: colors.text, fontSize: 15, fontWeight: '700' },
  itemMeta: { color: colors.textSecondary, fontSize: 12, marginTop: 4 },
  badgeBase: {
    borderRadius: 999,
    paddingHorizontal: 10,
    paddingVertical: 5,
    alignSelf: 'flex-start',
  },
  badgePending: { backgroundColor: '#FEF3C7' },
  badgeSuccess: { backgroundColor: '#DCFCE7' },
  badgeDanger: { backgroundColor: '#FEE2E2' },
  badgeText: { color: colors.text, fontSize: 11, fontWeight: '700' },
  bodyText: { color: colors.text, fontSize: 13, lineHeight: 19 },
  inlineText: { color: colors.textSecondary, fontSize: 12 },
  footerMeta: { color: colors.textMuted, fontSize: 11 },
  noteBox: {
    borderRadius: radius.md,
    backgroundColor: colors.bg2,
    padding: spacing.md,
    gap: 4,
  },
  noteLabel: { color: colors.textSecondary, fontSize: 11, fontWeight: '700' },
  noteText: { color: colors.text, fontSize: 13, lineHeight: 19 },
  emptyCard: {
    backgroundColor: colors.bg,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderStyle: 'dashed',
    borderColor: colors.borderStrong,
    paddingVertical: 40,
    alignItems: 'center',
  },
  emptyText: { color: colors.textSecondary, fontSize: 13 },
})
