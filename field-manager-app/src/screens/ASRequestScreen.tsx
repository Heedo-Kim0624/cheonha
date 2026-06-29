import React, { useState } from 'react'
import {
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { useNavigation } from '@react-navigation/native'
import { NativeStackNavigationProp } from '@react-navigation/native-stack'

import { colors, radius, spacing } from '../theme'
import { api, getIdentity } from '../services/api'
import { RootStackParamList } from '../navigation/types'

type Nav = NativeStackNavigationProp<RootStackParamList, 'ASRequest'>

export default function ASRequestScreen() {
  const nav = useNavigation<Nav>()
  const [vehicleNumber, setVehicleNumber] = useState('')
  const [ownerName, setOwnerName] = useState('')
  const [ownerPhone, setOwnerPhone] = useState('')
  const [reason, setReason] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const submit = async () => {
    if (!vehicleNumber.trim() || !ownerName.trim() || !ownerPhone.trim() || !reason.trim()) {
      Alert.alert('알림', '차량번호, 차량 차주, 운영 차주 전화번호, 사유를 모두 입력해주세요.')
      return
    }

    const identity = await getIdentity()
    if (!identity) {
      nav.replace('Login')
      return
    }

    setSubmitting(true)
    try {
      const { error } = await api.createASRequest({
        company_code: identity.company_code,
        team_code: identity.team_code,
        phone: identity.phone,
        vehicle_number: vehicleNumber.trim(),
        owner_name: ownerName.trim(),
        owner_phone: ownerPhone.trim(),
        reason: reason.trim(),
      })

      if (error) {
        Alert.alert('실패', error)
        return
      }

      Alert.alert('완료', 'A/S 요청이 등록되었습니다.', [
        { text: '확인', onPress: () => nav.navigate('Main') },
      ])
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <SafeAreaView style={styles.safe}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => nav.goBack()}>
          <Text style={styles.back}>뒤로</Text>
        </TouchableOpacity>
        <Text style={styles.title}>A/S 요청</Text>
        <View style={styles.headerSpacer} />
      </View>

      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={styles.body} keyboardShouldPersistTaps="handled">
          <View style={styles.notice}>
            <Text style={styles.noticeTitle}>A/S 접수 안내</Text>
            <Text style={styles.noticeText}>차량 정보와 차주 연락처를 정확하게 입력해야 웹에서 바로 처리할 수 있습니다.</Text>
          </View>

          <Text style={styles.label}>차량번호 *</Text>
          <TextInput
            value={vehicleNumber}
            onChangeText={setVehicleNumber}
            placeholder="예: 12가3456"
            style={[styles.input, styles.primaryBorder]}
          />

          <Text style={styles.label}>차량 차주 *</Text>
          <TextInput
            value={ownerName}
            onChangeText={setOwnerName}
            placeholder="차량 차주 성함"
            style={styles.input}
          />

          <Text style={styles.label}>운영 차주 전화번호 *</Text>
          <TextInput
            value={ownerPhone}
            onChangeText={setOwnerPhone}
            placeholder="010-1234-5678"
            keyboardType="phone-pad"
            style={styles.input}
          />

          <Text style={styles.label}>A/S 사유 *</Text>
          <TextInput
            value={reason}
            onChangeText={setReason}
            placeholder="예: 시동 불량, 브레이크 소음"
            style={[styles.input, styles.reasonInput]}
            multiline
          />

          <TouchableOpacity style={[styles.submit, submitting && styles.submitDisabled]} disabled={submitting} onPress={submit}>
            <Text style={styles.submitText}>{submitting ? '등록 중...' : 'A/S 요청 등록'}</Text>
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
  body: { padding: spacing.lg, gap: 14, paddingBottom: 40 },
  notice: {
    borderRadius: radius.lg,
    backgroundColor: '#FFF7ED',
    borderWidth: 1,
    borderColor: '#FED7AA',
    padding: spacing.lg,
    gap: 4,
  },
  noticeTitle: { color: '#C2410C', fontSize: 14, fontWeight: '700' },
  noticeText: { color: '#9A3412', fontSize: 12, lineHeight: 18 },
  label: { fontSize: 12, fontWeight: '700', color: colors.text, marginTop: 4 },
  input: {
    minHeight: 48,
    paddingHorizontal: 14,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.bg,
    fontSize: 14,
  },
  primaryBorder: {
    borderWidth: 2,
    borderColor: colors.primary,
  },
  reasonInput: {
    height: 120,
    textAlignVertical: 'top',
    paddingTop: 12,
  },
  submit: {
    marginTop: 20,
    height: 56,
    backgroundColor: colors.warning,
    borderRadius: radius.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  submitDisabled: {
    opacity: 0.7,
  },
  submitText: { fontSize: 15, fontWeight: '700', color: colors.textInverse },
})
