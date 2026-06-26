import React, { useState } from 'react'
import {
  ActivityIndicator, Alert, KeyboardAvoidingView, Platform,
  ScrollView, StyleSheet, Text, TextInput, TouchableOpacity, View,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { useNavigation } from '@react-navigation/native'
import { NativeStackNavigationProp } from '@react-navigation/native-stack'
import { colors, radius, spacing } from '../theme'
import { api, saveSession } from '../services/api'
import { RootStackParamList } from '../navigation/types'

type Nav = NativeStackNavigationProp<RootStackParamList, 'Login'>

const COMPANIES: { code: 'YUHAN' | 'CHEONHA' | 'PERSONAL'; name: string }[] = [
  { code: 'YUHAN', name: '유한' },
  { code: 'CHEONHA', name: '천하' },
  { code: 'PERSONAL', name: '개인' },
]

export default function LoginScreen() {
  const nav = useNavigation<Nav>()
  const [companyCode, setCompanyCode] = useState<'YUHAN' | 'CHEONHA' | 'PERSONAL'>('CHEONHA')
  const [teamCode, setTeamCode] = useState('')
  const [phone, setPhone] = useState('')
  const [pin, setPin] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async () => {
    if (!teamCode || !phone || !pin) {
      Alert.alert('알림', '조 / 전화번호 / 비밀번호를 모두 입력해 주세요.')
      return
    }
    setLoading(true)
    const { data, error } = await api.login(companyCode, teamCode.trim(), phone.trim(), pin)
    setLoading(false)
    if (error) {
      Alert.alert('로그인 실패', error)
      return
    }
    if (data) {
      await saveSession(data.token, data.identity)
      nav.replace('Main')
    }
  }

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <View style={styles.logo}>
            <View style={styles.logoCircle}>
              <Text style={{ fontSize: 36 }}>👷</Text>
            </View>
            <Text style={styles.appName}>CLEVER 현장관리자</Text>
            <Text style={styles.appDesc}>현장관리자 로그인</Text>
          </View>

          <Text style={styles.label}>회사 *</Text>
          <View style={styles.row}>
            {COMPANIES.map((c) => (
              <TouchableOpacity key={c.code}
                style={[styles.companyBtn, companyCode === c.code && styles.companyBtnActive]}
                onPress={() => setCompanyCode(c.code)}>
                <Text style={[styles.companyTxt, companyCode === c.code && styles.companyTxtActive]}>{c.name}</Text>
              </TouchableOpacity>
            ))}
          </View>

          <Text style={styles.label}>조 (예: H, A, R) *</Text>
          <TextInput value={teamCode} onChangeText={setTeamCode}
            placeholder="조" placeholderTextColor={colors.textMuted}
            style={styles.input} autoCapitalize="characters" maxLength={4} />

          <Text style={styles.label}>전화번호 *</Text>
          <TextInput value={phone} onChangeText={setPhone}
            placeholder="010-0000-0000" placeholderTextColor={colors.textMuted}
            style={styles.input} keyboardType="phone-pad" />

          <Text style={styles.label}>비밀번호 *</Text>
          <TextInput value={pin} onChangeText={(v) => setPin(v.replace(/\D/g, '').slice(0, 4))}
            placeholder="공통 비밀번호" placeholderTextColor={colors.textMuted}
            style={styles.input} keyboardType="number-pad" maxLength={4} secureTextEntry />
          <Text style={styles.hint}>공통 비밀번호: 2580</Text>

          <TouchableOpacity style={styles.submitBtn} onPress={submit} disabled={loading}>
            {loading
              ? <ActivityIndicator color={colors.textInverse} />
              : <Text style={styles.submitTxt}>로그인</Text>}
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.bg },
  scroll: { padding: spacing.xl, paddingTop: 40 },
  logo: { alignItems: 'center', marginBottom: 32, gap: 10 },
  logoCircle: { width: 80, height: 80, borderRadius: 40, backgroundColor: colors.primary,
    alignItems: 'center', justifyContent: 'center' },
  appName: { fontSize: 22, fontWeight: '700', color: colors.primary },
  appDesc: { fontSize: 13, color: colors.textSecondary },
  label: { fontSize: 13, fontWeight: '700', color: colors.text, marginTop: 18, marginBottom: 6 },
  row: { flexDirection: 'row', gap: spacing.sm },
  companyBtn: { flex: 1, paddingVertical: 14, borderRadius: radius.md,
    backgroundColor: colors.bg2, borderWidth: 1, borderColor: colors.border,
    alignItems: 'center' },
  companyBtnActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  companyTxt: { fontSize: 14, fontWeight: '700', color: colors.text },
  companyTxtActive: { color: colors.textInverse },
  input: { height: 52, paddingHorizontal: 14, borderRadius: radius.md,
    borderWidth: 1, borderColor: colors.border, fontSize: 14, color: colors.text },
  hint: { fontSize: 11, color: colors.textSecondary, marginTop: 6 },
  submitBtn: { marginTop: 28, height: 56, borderRadius: radius.md,
    backgroundColor: colors.primary, alignItems: 'center', justifyContent: 'center' },
  submitTxt: { fontSize: 15, fontWeight: '700', color: colors.textInverse },
})
