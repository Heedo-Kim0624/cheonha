import React, { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { useNavigation } from '@react-navigation/native'
import { NativeStackNavigationProp } from '@react-navigation/native-stack'

import CalendarDateField from '../components/CalendarDateField'
import { RootStackParamList } from '../navigation/types'
import { api, getIdentity } from '../services/api'
import { colors, radius, spacing } from '../theme'

type Nav = NativeStackNavigationProp<RootStackParamList, 'SubscriptionRequest'>

function todayIso() {
  return new Date().toISOString().slice(0, 10)
}

function oneYearLaterIso() {
  const next = new Date()
  next.setFullYear(next.getFullYear() + 1)
  return next.toISOString().slice(0, 10)
}

export default function SubscriptionRequestScreen() {
  const nav = useNavigation<Nav>()
  const [date, setDate] = useState(todayIso())
  const [qty, setQty] = useState(1)
  const [blockedDates, setBlockedDates] = useState<string[]>([])
  const minimumDate = useMemo(() => todayIso(), [])
  const blockedSet = useMemo(() => new Set(blockedDates), [blockedDates])
  const isBlocked = blockedSet.has(date)

  useEffect(() => {
    ;(async () => {
      const identity = await getIdentity()
      if (!identity) {
        nav.replace('Login')
        return
      }
      const response = await api.getBlockedDates(
        identity.company_code,
        todayIso(),
        oneYearLaterIso(),
      )
      if (response.data) {
        setBlockedDates(response.data.blocked_dates)
      }
    })()
  }, [nav])

  const submit = async () => {
    if (!date) {
      Alert.alert('알림', '날짜를 선택해주세요.')
      return
    }
    if (qty < 1) {
      Alert.alert('알림', '수량은 1대 이상이어야 합니다.')
      return
    }
    if (isBlocked) {
      Alert.alert('알림', '공휴일 또는 신청 불가 날짜는 선택할 수 없습니다.')
      return
    }

    const identity = await getIdentity()
    if (!identity) {
      nav.replace('Login')
      return
    }

    const { error } = await api.createSubscriptionRequest({
      company_code: identity.company_code,
      team_code: identity.team_code,
      phone: identity.phone,
      requested_date: date,
      quantity: qty,
    })

    if (error) {
      Alert.alert('신청 실패', error)
      return
    }

    Alert.alert('완료', '구독 요청이 등록되었습니다.', [
      { text: '확인', onPress: () => nav.navigate('Main') },
    ])
  }

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => nav.goBack()}>
          <Text style={styles.back}>뒤로</Text>
        </TouchableOpacity>
        <Text style={styles.title}>구독 요청</Text>
        <View style={styles.headerSpacer} />
      </View>

      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={styles.body} keyboardShouldPersistTaps="handled">
          <View style={styles.notice}>
            <Text style={styles.noticeTitle}>구독 요청 안내</Text>
            <Text style={styles.noticeText}>필요한 날짜와 차량 수량을 입력하면 바로 요청이 등록됩니다.</Text>
            <Text style={styles.noticeText}>공휴일과 신청 불가 날짜는 캘린더에서 선택할 수 없습니다.</Text>
          </View>

          <CalendarDateField
            label="요청 날짜 *"
            value={date}
            onChange={setDate}
            minimumDate={minimumDate}
            blockedDates={blockedDates}
            helperText={
              isBlocked
                ? '선택한 날짜는 신청할 수 없습니다.'
                : '공휴일과 신청 불가 날짜는 선택되지 않습니다.'
            }
          />

          <View style={styles.quantityCard}>
            <Text style={styles.quantityLabel}>요청 수량 *</Text>
            <View style={styles.qtyRow}>
              <TouchableOpacity style={styles.qtyButton} onPress={() => setQty(Math.max(1, qty - 1))}>
                <Text style={styles.qtyButtonText}>-</Text>
              </TouchableOpacity>
              <Text style={styles.qtyValue}>{qty}</Text>
              <TouchableOpacity
                style={[styles.qtyButton, styles.qtyButtonPrimary]}
                onPress={() => setQty(qty + 1)}
              >
                <Text style={[styles.qtyButtonText, styles.qtyButtonTextPrimary]}>+</Text>
              </TouchableOpacity>
            </View>
            <Text style={styles.qtyHint}>1대 이상 요청할 수 있습니다.</Text>
          </View>

          <TouchableOpacity
            style={[styles.submit, isBlocked && styles.submitDisabled]}
            onPress={submit}
            disabled={isBlocked}
          >
            <Text style={styles.submitText}>요청 등록</Text>
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>
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
  headerSpacer: { width: 36 },
  body: { padding: spacing.lg, gap: spacing.lg, paddingBottom: 40 },
  notice: {
    borderRadius: radius.lg,
    backgroundColor: '#EFF6FF',
    borderWidth: 1,
    borderColor: '#BFDBFE',
    padding: spacing.lg,
    gap: 4,
  },
  noticeTitle: { color: colors.primary, fontSize: 14, fontWeight: '700' },
  noticeText: { color: colors.primary, fontSize: 12, lineHeight: 18 },
  quantityCard: {
    borderRadius: radius.lg,
    backgroundColor: colors.bg,
    borderWidth: 1,
    borderColor: colors.border,
    padding: spacing.lg,
    gap: spacing.md,
  },
  quantityLabel: { color: colors.text, fontSize: 13, fontWeight: '700' },
  qtyRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
  },
  qtyButton: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.bg2,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  qtyButtonPrimary: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  qtyButtonText: { color: colors.text, fontSize: 22, fontWeight: '700' },
  qtyButtonTextPrimary: { color: colors.textInverse },
  qtyValue: { minWidth: 40, textAlign: 'center', color: colors.text, fontSize: 24, fontWeight: '700' },
  qtyHint: { color: colors.textSecondary, fontSize: 12 },
  submit: {
    marginTop: 6,
    height: 56,
    borderRadius: radius.md,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  submitDisabled: { backgroundColor: colors.borderStrong },
  submitText: { color: colors.textInverse, fontSize: 15, fontWeight: '700' },
})
