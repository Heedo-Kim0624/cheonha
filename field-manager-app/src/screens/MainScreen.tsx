import React, { useEffect, useMemo, useState } from 'react'
import { Pressable, ScrollView, StyleSheet, Text, TouchableOpacity, View } from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { useNavigation } from '@react-navigation/native'
import { NativeStackNavigationProp } from '@react-navigation/native-stack'

import { colors, radius, spacing } from '../theme'
import { clearSession, getIdentity, Identity } from '../services/api'
import { RootStackParamList } from '../navigation/types'

type Nav = NativeStackNavigationProp<RootStackParamList, 'Main'>

const COMPANY_LABEL: Record<string, string> = {
  YUHAN: '유한',
  CHEONHA: '천하',
  PERSONAL: '개인',
}

const MENU_ITEMS: Array<{
  title: string
  description: string
  route: keyof RootStackParamList
}> = [
  {
    title: '구독 요청',
    description: '필요한 차량 대수와 날짜를 선택해 구독 요청을 등록합니다.',
    route: 'SubscriptionRequest',
  },
  {
    title: '구독 반납',
    description: '반납 일정과 차량 사진 5장을 함께 제출합니다.',
    route: 'SubscriptionReturn',
  },
  {
    title: 'A/S 요청',
    description: '차주 정보와 고장 사유를 입력해 A/S를 접수합니다.',
    route: 'ASRequest',
  },
  {
    title: '요청 이력',
    description: '승인·반려·조정 사유와 이전 요청 이력을 확인합니다.',
    route: 'RequestHistory',
  },
]

export default function MainScreen() {
  const nav = useNavigation<Nav>()
  const [identity, setIdentity] = useState<Identity | null>(null)

  useEffect(() => {
    getIdentity().then(setIdentity)
  }, [])

  const companyLabel = useMemo(() => {
    if (!identity) return ''
    return COMPANY_LABEL[identity.company_code] || identity.company_code
  }, [identity])

  const logout = async () => {
    await clearSession()
    nav.replace('Login')
  }

  return (
    <SafeAreaView style={styles.safe}>
      <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
        <View style={styles.hero}>
          <Text style={styles.heroKicker}>CLEVER 현장관리자</Text>
          <Text style={styles.heroTitle}>
            {companyLabel} · {identity?.team_code || '-'}조
          </Text>
          <Text style={styles.heroMeta}>{identity?.phone || ''}</Text>
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>업무 메뉴</Text>
          <Text style={styles.sectionCaption}>
            요청 등록, 반납 사진 제출, A/S 접수, 처리 이력을 빠르게 확인할 수 있게 정리했습니다.
          </Text>
        </View>

        <View style={styles.menuList}>
          {MENU_ITEMS.map((item) => (
            <Pressable
              key={item.route}
              style={({ pressed }) => [styles.menuCard, pressed && styles.menuCardPressed]}
              onPress={() => nav.push(item.route)}
            >
              <View style={{ flex: 1 }}>
                <Text style={styles.menuTitle}>{item.title}</Text>
                <Text style={styles.menuDescription}>{item.description}</Text>
              </View>
              <Text style={styles.menuArrow}>열기</Text>
            </Pressable>
          ))}
        </View>

        <View style={styles.noticeCard}>
          <Text style={styles.noticeTitle}>반납 요청 제출 기준</Text>
          <Text style={styles.noticeText}>전면, 후면, 좌측, 우측, 내부 대시보드 사진 5장이 모두 필요합니다.</Text>
          <Text style={styles.noticeText}>
            내부 대시보드 사진에는 키로수와 하이패스 기기가 함께 보이도록 촬영해야 합니다.
          </Text>
        </View>

        <TouchableOpacity style={styles.logoutButton} onPress={logout}>
          <Text style={styles.logoutText}>로그아웃</Text>
        </TouchableOpacity>
      </ScrollView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg2 },
  content: { padding: spacing.lg, gap: spacing.md, paddingBottom: 40 },
  hero: {
    backgroundColor: colors.primary,
    borderRadius: radius.lg,
    padding: spacing.xl,
    gap: 6,
  },
  heroKicker: { color: '#D6E4F1', fontSize: 12, fontWeight: '700' },
  heroTitle: { color: colors.textInverse, fontSize: 22, fontWeight: '700' },
  heroMeta: { color: '#E2E8F0', fontSize: 13, fontWeight: '600' },
  section: { gap: 4, marginTop: 4 },
  sectionTitle: { color: colors.text, fontSize: 16, fontWeight: '700' },
  sectionCaption: { color: colors.textSecondary, fontSize: 12 },
  menuList: { gap: spacing.sm },
  menuCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.bg,
    padding: spacing.lg,
  },
  menuCardPressed: {
    backgroundColor: colors.bg2,
    borderColor: colors.primary,
  },
  menuTitle: { color: colors.text, fontSize: 15, fontWeight: '700' },
  menuDescription: { color: colors.textSecondary, fontSize: 12, marginTop: 6, lineHeight: 18 },
  menuArrow: { color: colors.primary, fontSize: 12, fontWeight: '700' },
  noticeCard: {
    borderRadius: radius.lg,
    backgroundColor: '#EFF6FF',
    borderWidth: 1,
    borderColor: '#BFDBFE',
    padding: spacing.lg,
    gap: 6,
  },
  noticeTitle: { color: colors.primary, fontSize: 14, fontWeight: '700' },
  noticeText: { color: colors.primary, fontSize: 12, lineHeight: 18 },
  logoutButton: {
    marginTop: 8,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.borderStrong,
    backgroundColor: colors.bg,
    paddingVertical: 14,
    alignItems: 'center',
  },
  logoutText: { color: colors.textSecondary, fontSize: 13, fontWeight: '700' },
})
