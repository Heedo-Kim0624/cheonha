import React, { useEffect, useMemo, useState } from 'react'
import {
  Alert,
  Image,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native'
import * as ImagePicker from 'expo-image-picker'
import { SafeAreaView } from 'react-native-safe-area-context'
import { useNavigation } from '@react-navigation/native'
import { NativeStackNavigationProp } from '@react-navigation/native-stack'

import { colors, radius, spacing } from '../theme'
import { api, getIdentity, Identity, LocalImageFile } from '../services/api'
import { RootStackParamList } from '../navigation/types'
import CalendarDateField from '../components/CalendarDateField'

type Nav = NativeStackNavigationProp<RootStackParamList, 'SubscriptionReturn'>

const HOURS = ['10:00', '11:00', '12:00', '13:00', '14:00', '15:00', '16:00']

const PHOTO_FIELDS = [
  { key: 'front', label: '차량 전면', note: '차량 번호가 보이도록 촬영' },
  { key: 'rear', label: '차량 후면', note: '후면 전체 상태가 보이도록 촬영' },
  { key: 'left', label: '차량 좌측', note: '문과 판금 상태가 보이도록 촬영' },
  { key: 'right', label: '차량 우측', note: '문과 판금 상태가 보이도록 촬영' },
  {
    key: 'dashboard',
    label: '내부 대시보드',
    note: '키로수와 하이패스 기기가 같이 보이도록 촬영',
  },
] as const

type PhotoKey = (typeof PHOTO_FIELDS)[number]['key']
type ReturnPhotos = Record<PhotoKey, LocalImageFile | null>

function todayIso() {
  return new Date().toISOString().slice(0, 10)
}

function oneYearLaterIso() {
  const next = new Date()
  next.setFullYear(next.getFullYear() + 1)
  return next.toISOString().slice(0, 10)
}

export default function SubscriptionReturnScreen() {
  const nav = useNavigation<Nav>()
  const [identity, setIdentity] = useState<Identity | null>(null)
  const [vehicleNumber, setVehicleNumber] = useState('')
  const [reason, setReason] = useState('')
  const [date, setDate] = useState(todayIso())
  const [time, setTime] = useState('10:00')
  const [blockedDates, setBlockedDates] = useState<string[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [photos, setPhotos] = useState<ReturnPhotos>({
    front: null,
    rear: null,
    left: null,
    right: null,
    dashboard: null,
  })

  useEffect(() => {
    ;(async () => {
      const id = await getIdentity()
      setIdentity(id)
      if (!id) {
        return
      }
      const response = await api.getBlockedDates(id.company_code, todayIso(), oneYearLaterIso())
      if (response.data) {
        setBlockedDates(response.data.blocked_dates)
      }
    })()
  }, [])

  const blockedSet = useMemo(() => new Set(blockedDates), [blockedDates])
  const isBlocked = blockedSet.has(date)

  const pickImage = async (photoKey: PhotoKey, source: 'camera' | 'library') => {
    const permission =
      source === 'camera'
        ? await ImagePicker.requestCameraPermissionsAsync()
        : await ImagePicker.requestMediaLibraryPermissionsAsync()

    if (!permission.granted) {
      Alert.alert(
        '권한 필요',
        source === 'camera' ? '카메라 권한이 필요합니다.' : '사진 접근 권한이 필요합니다.',
      )
      return
    }

    const result =
      source === 'camera'
        ? await ImagePicker.launchCameraAsync({
            mediaTypes: ImagePicker.MediaTypeOptions.Images,
            allowsEditing: false,
            quality: 0.8,
          })
        : await ImagePicker.launchImageLibraryAsync({
            mediaTypes: ImagePicker.MediaTypeOptions.Images,
            allowsEditing: false,
            quality: 0.8,
          })

    if (result.canceled || !result.assets.length) {
      return
    }

    const asset = result.assets[0]
    setPhotos((prev) => ({
      ...prev,
      [photoKey]: {
        uri: asset.uri,
        name: asset.fileName || `${photoKey}.jpg`,
        type: asset.mimeType || 'image/jpeg',
      },
    }))
  }

  const clearPhoto = (photoKey: PhotoKey) => {
    setPhotos((prev) => ({ ...prev, [photoKey]: null }))
  }

  const validate = () => {
    if (!vehicleNumber.trim() || !reason.trim() || !date || !time) {
      Alert.alert('알림', '차량번호, 사유, 반납 날짜, 시간을 모두 입력해주세요.')
      return false
    }
    if (isBlocked) {
      Alert.alert('알림', '선택한 날짜는 반납 불가일입니다. 다른 날짜를 선택해주세요.')
      return false
    }
    const missing = PHOTO_FIELDS.find((item) => !photos[item.key])
    if (missing) {
      Alert.alert('알림', `${missing.label} 사진을 등록해주세요.`)
      return false
    }
    return true
  }

  const submit = async () => {
    if (!validate()) return
    if (!identity) {
      nav.replace('Login')
      return
    }

    setSubmitting(true)
    try {
      const { error } = await api.createReturnRequest({
        company_code: identity.company_code,
        team_code: identity.team_code,
        phone: identity.phone,
        vehicle_number: vehicleNumber.trim(),
        reason: reason.trim(),
        hope_date: date,
        hope_time: `${time}:00`,
        photos: {
          front: photos.front!,
          rear: photos.rear!,
          left: photos.left!,
          right: photos.right!,
          dashboard: photos.dashboard!,
        },
      })

      if (error) {
        Alert.alert('실패', error)
        return
      }

      Alert.alert('완료', '반납 요청이 등록되었습니다.', [
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
        <Text style={styles.title}>구독 반납</Text>
        <View style={styles.headerSpacer} />
      </View>

      <KeyboardAvoidingView style={{ flex: 1 }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView contentContainerStyle={styles.body} keyboardShouldPersistTaps="handled">
          <View style={styles.notice}>
            <Text style={styles.noticeTitle}>반납 요청 기준</Text>
            <Text style={styles.noticeText}>차량 상태 사진 5장을 모두 등록해야 반납 요청을 보낼 수 있습니다.</Text>
            <Text style={styles.noticeText}>공휴일과 반납 불가일은 달력에서 선택되지 않습니다.</Text>
          </View>

          <Text style={styles.label}>차량번호 *</Text>
          <TextInput
            value={vehicleNumber}
            onChangeText={setVehicleNumber}
            placeholder="예: 12가3456"
            style={styles.input}
          />

          <Text style={styles.label}>반납 사유 *</Text>
          <TextInput
            value={reason}
            onChangeText={setReason}
            placeholder="예: 사용 종료 / 차량 교체"
            style={[styles.input, styles.reasonInput]}
            multiline
          />

          <CalendarDateField
            label="반납 희망 날짜 *"
            value={date}
            onChange={setDate}
            minimumDate={todayIso()}
            blockedDates={blockedDates}
            helperText={
              isBlocked
                ? '선택한 날짜는 반납 불가일입니다.'
                : '공휴일과 반납 불가일은 회색으로 표시됩니다.'
            }
          />

          <View style={styles.sectionCard}>
            <Text style={styles.sectionTitle}>반납 희망 시간 *</Text>
            <View style={styles.timeGrid}>
              {HOURS.map((hour) => (
                <TouchableOpacity
                  key={hour}
                  style={[styles.timeButton, time === hour && styles.timeButtonActive]}
                  onPress={() => setTime(hour)}
                >
                  <Text style={[styles.timeText, time === hour && styles.timeTextActive]}>{hour}</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>

          <View style={styles.sectionCard}>
            <Text style={styles.sectionTitle}>반납 사진 5장 *</Text>
            <Text style={styles.sectionHelper}>촬영 또는 앨범 선택으로 등록할 수 있습니다.</Text>

            <View style={styles.photoList}>
              {PHOTO_FIELDS.map((field) => {
                const photo = photos[field.key]
                return (
                  <View key={field.key} style={styles.photoCard}>
                    <View style={styles.photoHeader}>
                      <View style={{ flex: 1 }}>
                        <Text style={styles.photoTitle}>{field.label}</Text>
                        <Text style={styles.photoNote}>{field.note}</Text>
                      </View>
                      {photo ? <Text style={styles.photoDone}>등록됨</Text> : null}
                    </View>

                    {photo ? (
                      <Image source={{ uri: photo.uri }} style={styles.photoPreview} />
                    ) : (
                      <View style={styles.photoPlaceholder}>
                        <Text style={styles.photoPlaceholderText}>사진 미등록</Text>
                      </View>
                    )}

                    <View style={styles.photoActions}>
                      <TouchableOpacity style={styles.photoButton} onPress={() => pickImage(field.key, 'camera')}>
                        <Text style={styles.photoButtonText}>촬영</Text>
                      </TouchableOpacity>
                      <TouchableOpacity style={styles.photoButton} onPress={() => pickImage(field.key, 'library')}>
                        <Text style={styles.photoButtonText}>앨범</Text>
                      </TouchableOpacity>
                      {photo ? (
                        <TouchableOpacity
                          style={[styles.photoButton, styles.photoButtonDanger]}
                          onPress={() => clearPhoto(field.key)}
                        >
                          <Text style={styles.photoButtonDangerText}>삭제</Text>
                        </TouchableOpacity>
                      ) : null}
                    </View>
                  </View>
                )
              })}
            </View>
          </View>

          <TouchableOpacity
            style={[styles.submit, (isBlocked || submitting) && styles.submitDisabled]}
            disabled={isBlocked || submitting}
            onPress={submit}
          >
            <Text style={styles.submitText}>
              {submitting ? '등록 중...' : '반납 요청 등록'}
            </Text>
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
  body: { padding: spacing.lg, gap: spacing.lg, paddingBottom: 48 },
  notice: {
    borderRadius: radius.lg,
    backgroundColor: '#FEF2F2',
    borderWidth: 1,
    borderColor: '#FECACA',
    padding: spacing.lg,
    gap: 4,
  },
  noticeTitle: { color: colors.danger, fontSize: 14, fontWeight: '700' },
  noticeText: { color: colors.danger, fontSize: 12, lineHeight: 18 },
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
  reasonInput: { height: 96, textAlignVertical: 'top', paddingTop: 12 },
  sectionCard: {
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.bg,
    padding: spacing.lg,
    gap: spacing.md,
  },
  sectionTitle: { color: colors.text, fontSize: 14, fontWeight: '700' },
  sectionHelper: { color: colors.textSecondary, fontSize: 12 },
  timeGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  timeButton: {
    width: '23%',
    height: 42,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.bg2,
  },
  timeButtonActive: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  timeText: { color: colors.text, fontSize: 12, fontWeight: '700' },
  timeTextActive: { color: colors.textInverse },
  photoList: { gap: spacing.md },
  photoCard: {
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.bg2,
    padding: spacing.md,
    gap: spacing.sm,
  },
  photoHeader: { flexDirection: 'row', justifyContent: 'space-between', gap: spacing.md },
  photoTitle: { color: colors.text, fontSize: 13, fontWeight: '700' },
  photoNote: { color: colors.textSecondary, fontSize: 11, marginTop: 4, lineHeight: 16 },
  photoDone: { color: colors.success, fontSize: 11, fontWeight: '700' },
  photoPreview: { width: '100%', height: 180, borderRadius: radius.sm, backgroundColor: '#E5E7EB' },
  photoPlaceholder: {
    height: 96,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderStyle: 'dashed',
    borderColor: colors.borderStrong,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.bg,
  },
  photoPlaceholderText: { color: colors.textMuted, fontSize: 12 },
  photoActions: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  photoButton: {
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.bg,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  photoButtonText: { color: colors.text, fontSize: 12, fontWeight: '700' },
  photoButtonDanger: { borderColor: '#FECACA', backgroundColor: '#FEF2F2' },
  photoButtonDangerText: { color: colors.danger, fontSize: 12, fontWeight: '700' },
  submit: {
    height: 56,
    borderRadius: radius.md,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  submitDisabled: { backgroundColor: colors.borderStrong },
  submitText: { color: colors.textInverse, fontSize: 15, fontWeight: '700' },
})
