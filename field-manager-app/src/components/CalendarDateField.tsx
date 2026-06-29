import React from 'react'
import {
  Modal,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native'

import { colors, radius, spacing } from '../theme'

interface CalendarDateFieldProps {
  label: string
  value: string
  onChange: (next: string) => void
  helperText?: string
  blockedDates?: string[]
  minimumDate?: string
  maximumDate?: string
}

const WEEKDAY_LABELS = ['일', '월', '화', '수', '목', '금', '토']

function parseIsoDate(value?: string) {
  if (!value) return new Date()
  const parsed = new Date(`${value}T00:00:00`)
  return Number.isNaN(parsed.getTime()) ? new Date() : parsed
}

function toIsoDate(value: Date) {
  const year = value.getFullYear()
  const month = String(value.getMonth() + 1).padStart(2, '0')
  const day = String(value.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function startOfMonth(value: Date) {
  return new Date(value.getFullYear(), value.getMonth(), 1)
}

function addMonths(value: Date, diff: number) {
  return new Date(value.getFullYear(), value.getMonth() + diff, 1)
}

function formatMonthLabel(value: Date) {
  return `${value.getFullYear()}년 ${value.getMonth() + 1}월`
}

function buildCalendarCells(monthDate: Date) {
  const firstDay = startOfMonth(monthDate)
  const startWeekday = firstDay.getDay()
  const startDate = new Date(firstDay)
  startDate.setDate(firstDay.getDate() - startWeekday)

  return Array.from({ length: 42 }, (_, index) => {
    const cellDate = new Date(startDate)
    cellDate.setDate(startDate.getDate() + index)
    return {
      date: cellDate,
      iso: toIsoDate(cellDate),
      isCurrentMonth: cellDate.getMonth() === monthDate.getMonth(),
    }
  })
}

export default function CalendarDateField({
  label,
  value,
  onChange,
  helperText,
  blockedDates = [],
  minimumDate,
  maximumDate,
}: CalendarDateFieldProps) {
  const blockedSet = React.useMemo(() => new Set(blockedDates), [blockedDates])
  const [visible, setVisible] = React.useState(false)
  const [currentMonth, setCurrentMonth] = React.useState(() => startOfMonth(parseIsoDate(value || minimumDate)))

  React.useEffect(() => {
    if (!visible) {
      setCurrentMonth(startOfMonth(parseIsoDate(value || minimumDate)))
    }
  }, [minimumDate, value, visible])

  const calendarCells = React.useMemo(() => buildCalendarCells(currentMonth), [currentMonth])

  const isDisabled = React.useCallback(
    (iso: string) => {
      if (minimumDate && iso < minimumDate) return true
      if (maximumDate && iso > maximumDate) return true
      return blockedSet.has(iso)
    },
    [blockedSet, maximumDate, minimumDate],
  )

  const onSelectDate = (iso: string) => {
    if (isDisabled(iso)) {
      return
    }
    onChange(iso)
    setVisible(false)
  }

  return (
    <View style={styles.wrapper}>
      <Text style={styles.label}>{label}</Text>
      <TouchableOpacity
        style={styles.fieldButton}
        activeOpacity={0.85}
        onPress={() => setVisible(true)}
      >
        <Text style={styles.fieldValue}>{value || '날짜 선택'}</Text>
        <Text style={styles.fieldAction}>캘린더</Text>
      </TouchableOpacity>
      {helperText ? <Text style={styles.helperText}>{helperText}</Text> : null}

      {visible ? (
        <Modal
          animationType="fade"
          transparent
          visible={visible}
          onRequestClose={() => setVisible(false)}
        >
          <View style={styles.overlay}>
            <TouchableOpacity style={styles.backdrop} activeOpacity={1} onPress={() => setVisible(false)} />
            <View style={styles.sheet}>
              <View style={styles.sheetHeader}>
                <Text style={styles.sheetTitle}>날짜 선택</Text>
                <TouchableOpacity onPress={() => setVisible(false)}>
                  <Text style={styles.closeText}>닫기</Text>
                </TouchableOpacity>
              </View>

              <View style={styles.monthRow}>
                <TouchableOpacity style={styles.monthButton} onPress={() => setCurrentMonth((prev) => addMonths(prev, -1))}>
                  <Text style={styles.monthButtonText}>이전</Text>
                </TouchableOpacity>
                <Text style={styles.monthLabel}>{formatMonthLabel(currentMonth)}</Text>
                <TouchableOpacity style={styles.monthButton} onPress={() => setCurrentMonth((prev) => addMonths(prev, 1))}>
                  <Text style={styles.monthButtonText}>다음</Text>
                </TouchableOpacity>
              </View>

              <View style={styles.weekdayRow}>
                {WEEKDAY_LABELS.map((day, index) => (
                  <Text
                    key={day}
                    style={[
                      styles.weekdayText,
                      index === 0 && styles.sunText,
                      index === 6 && styles.satText,
                    ]}
                  >
                    {day}
                  </Text>
                ))}
              </View>

              <View style={styles.grid}>
                {calendarCells.map((cell, index) => {
                  const disabled = isDisabled(cell.iso)
                  const selected = cell.iso === value
                  return (
                    <TouchableOpacity
                      key={`${cell.iso}-${index}`}
                      style={[
                        styles.dayCell,
                        !cell.isCurrentMonth && styles.dayCellMuted,
                        disabled && styles.dayCellDisabled,
                        selected && styles.dayCellSelected,
                      ]}
                      onPress={() => onSelectDate(cell.iso)}
                      disabled={disabled}
                      activeOpacity={0.85}
                    >
                      <Text
                        style={[
                          styles.dayText,
                          !cell.isCurrentMonth && styles.dayTextMuted,
                          disabled && styles.dayTextDisabled,
                          selected && styles.dayTextSelected,
                          cell.date.getDay() === 0 && !disabled && styles.sunText,
                          cell.date.getDay() === 6 && !disabled && styles.satText,
                        ]}
                      >
                        {cell.date.getDate()}
                      </Text>
                    </TouchableOpacity>
                  )
                })}
              </View>

              <View style={styles.legendRow}>
                <View style={styles.legendItem}>
                  <View style={[styles.legendDot, styles.legendDotBlocked]} />
                  <Text style={styles.legendText}>선택 불가</Text>
                </View>
                <View style={styles.legendItem}>
                  <View style={[styles.legendDot, styles.legendDotSelected]} />
                  <Text style={styles.legendText}>현재 선택</Text>
                </View>
              </View>
            </View>
          </View>
        </Modal>
      ) : null}
    </View>
  )
}

const styles = StyleSheet.create({
  wrapper: { gap: 6 },
  label: { fontSize: 12, fontWeight: '700', color: colors.text, marginTop: 4 },
  fieldButton: {
    minHeight: 48,
    paddingHorizontal: 14,
    paddingVertical: 12,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.bg,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  fieldValue: { fontSize: 14, color: colors.text, fontWeight: '600' },
  fieldAction: { fontSize: 12, color: colors.primary, fontWeight: '700' },
  helperText: { fontSize: 11, color: colors.textSecondary, lineHeight: 16 },
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(15, 23, 42, 0.28)',
    justifyContent: 'center',
    padding: spacing.lg,
  },
  backdrop: {
    ...StyleSheet.absoluteFillObject,
  },
  sheet: {
    borderRadius: radius.lg,
    backgroundColor: colors.bg,
    padding: spacing.lg,
    gap: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
  },
  sheetHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  sheetTitle: { fontSize: 16, fontWeight: '700', color: colors.text },
  closeText: { fontSize: 13, fontWeight: '700', color: colors.primary },
  monthRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  monthButton: {
    minWidth: 64,
    height: 34,
    borderRadius: radius.sm,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.bg2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  monthButtonText: { fontSize: 12, color: colors.text, fontWeight: '700' },
  monthLabel: { fontSize: 14, color: colors.text, fontWeight: '700' },
  weekdayRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 2,
  },
  weekdayText: {
    width: '14.2%',
    textAlign: 'center',
    fontSize: 12,
    color: colors.textSecondary,
    fontWeight: '700',
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    rowGap: 8,
  },
  dayCell: {
    width: '14.28%',
    aspectRatio: 1,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radius.sm,
  },
  dayCellMuted: {
    opacity: 0.45,
  },
  dayCellDisabled: {
    backgroundColor: colors.dangerBg,
  },
  dayCellSelected: {
    backgroundColor: colors.primary,
  },
  dayText: {
    fontSize: 13,
    color: colors.text,
    fontWeight: '600',
  },
  dayTextMuted: {
    color: colors.textMuted,
  },
  dayTextDisabled: {
    color: colors.danger,
  },
  dayTextSelected: {
    color: colors.textInverse,
  },
  sunText: {
    color: colors.sun,
  },
  satText: {
    color: colors.sat,
  },
  legendRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs,
  },
  legendDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: colors.borderStrong,
  },
  legendDotBlocked: {
    backgroundColor: colors.danger,
  },
  legendDotSelected: {
    backgroundColor: colors.primary,
  },
  legendText: {
    fontSize: 11,
    color: colors.textSecondary,
  },
})
