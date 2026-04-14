import React from "react";
import {
  View,
  Text,
  TouchableOpacity,
  Modal,
  StyleSheet,
  FlatList,
  Pressable,
} from "react-native";
import { colors, typography } from "../theme";

const TEAM_CODES = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");

interface Props {
  visible: boolean;
  selected: string;
  onSelect: (code: string) => void;
  onClose: () => void;
}

export default function TeamCodePicker({
  visible,
  selected,
  onSelect,
  onClose,
}: Props) {
  return (
    <Modal
      visible={visible}
      transparent
      animationType="slide"
      onRequestClose={onClose}
    >
      <Pressable style={styles.overlay} onPress={onClose}>
        <Pressable style={styles.sheet}>
          <View style={styles.handle} />
          <Text style={styles.title}>소속 조 선택</Text>
          <FlatList
            data={TEAM_CODES}
            numColumns={6}
            keyExtractor={(item) => item}
            contentContainerStyle={styles.grid}
            renderItem={({ item }) => (
              <TouchableOpacity
                style={[
                  styles.codeCell,
                  item === selected && styles.codeCellActive,
                ]}
                onPress={() => onSelect(item)}
                activeOpacity={0.7}
              >
                <Text
                  style={[
                    styles.codeText,
                    item === selected && styles.codeTextActive,
                  ]}
                >
                  {item}
                </Text>
              </TouchableOpacity>
            )}
          />
        </Pressable>
      </Pressable>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.4)",
    justifyContent: "flex-end",
  },
  sheet: {
    backgroundColor: colors.bgPrimary,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    paddingBottom: 40,
    paddingHorizontal: 24,
    paddingTop: 12,
  },
  handle: {
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: colors.borderLight,
    alignSelf: "center",
    marginBottom: 16,
  },
  title: {
    ...typography.sectionTitle,
    color: colors.textPrimary,
    textAlign: "center",
    marginBottom: 20,
  },
  grid: {
    gap: 10,
  },
  codeCell: {
    flex: 1,
    aspectRatio: 1,
    maxWidth: "16%",
    margin: 2,
    borderRadius: 12,
    backgroundColor: colors.bgSecondary,
    justifyContent: "center",
    alignItems: "center",
  },
  codeCellActive: {
    backgroundColor: colors.accentBlue,
  },
  codeText: {
    ...typography.sectionTitle,
    color: colors.textPrimary,
  },
  codeTextActive: {
    color: colors.textInverse,
  },
});
