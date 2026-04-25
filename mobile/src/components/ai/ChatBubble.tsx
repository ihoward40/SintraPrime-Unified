import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Copy, Share2, BookmarkPlus } from 'lucide-react-native';
import * as Clipboard from 'expo-clipboard';
import * as Haptics from 'expo-haptics';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { Spacing, BorderRadius } from '@theme/spacing';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  citations?: string[];
  agentName?: string;
}

interface ChatBubbleProps {
  message: ChatMessage;
  onSave?: (message: ChatMessage) => void;
}

export default function ChatBubble({ message, onSave }: ChatBubbleProps) {
  const isUser = message.role === 'user';

  const handleCopy = async () => {
    await Clipboard.setStringAsync(message.content);
    await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
  };

  return (
    <View style={[styles.container, isUser && styles.userContainer]}>
      {!isUser && (
        <View style={styles.avatar}>
          <Text style={styles.avatarText}>SP</Text>
        </View>
      )}

      <View style={[styles.bubble, isUser ? styles.userBubble : styles.aiBubble]}>
        {!isUser && message.agentName && (
          <Text style={styles.agentName}>{message.agentName}</Text>
        )}

        <Text style={[styles.content, isUser && styles.userContent]}>
          {message.content}
        </Text>

        {/* Citations */}
        {message.citations && message.citations.length > 0 && (
          <View style={styles.citations}>
            <Text style={styles.citationsHeader}>Sources:</Text>
            {message.citations.map((cite, i) => (
              <Text key={i} style={styles.citation}>
                [{i + 1}] {cite}
              </Text>
            ))}
          </View>
        )}

        {/* Actions */}
        {!isUser && (
          <View style={styles.actions}>
            <TouchableOpacity onPress={handleCopy} style={styles.actionBtn}>
              <Copy size={12} color={Colors.textMuted} strokeWidth={2} />
            </TouchableOpacity>
            {onSave && (
              <TouchableOpacity onPress={() => onSave(message)} style={styles.actionBtn}>
                <BookmarkPlus size={12} color={Colors.textMuted} strokeWidth={2} />
              </TouchableOpacity>
            )}
          </View>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: Spacing.sm,
    paddingHorizontal: Spacing.base,
    marginBottom: Spacing.md,
  },
  userContainer: {
    flexDirection: 'row-reverse',
  },
  avatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: Colors.gold[500],
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  avatarText: {
    ...Typography.labelSmall,
    color: Colors.navy[900],
    fontWeight: '800',
  },
  bubble: {
    maxWidth: '80%',
    borderRadius: BorderRadius.xl,
    padding: Spacing.md,
    gap: Spacing.sm,
  },
  aiBubble: {
    backgroundColor: Colors.surfaceElevated,
    borderTopLeftRadius: 4,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  userBubble: {
    backgroundColor: Colors.gold[500],
    borderTopRightRadius: 4,
  },
  agentName: {
    ...Typography.labelSmall,
    color: Colors.gold[400],
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  content: {
    ...Typography.bodyMedium,
    color: Colors.textPrimary,
    lineHeight: 22,
  },
  userContent: {
    color: Colors.navy[900],
    fontWeight: '500',
  },
  citations: {
    borderTopWidth: 1,
    borderTopColor: Colors.border,
    paddingTop: Spacing.sm,
    gap: 2,
  },
  citationsHeader: {
    ...Typography.labelSmall,
    color: Colors.textMuted,
    textTransform: 'uppercase',
  },
  citation: {
    ...Typography.bodySmall,
    color: Colors.gold[400],
    fontStyle: 'italic',
  },
  actions: {
    flexDirection: 'row',
    gap: Spacing.sm,
    justifyContent: 'flex-end',
  },
  actionBtn: {
    padding: 4,
    borderRadius: 8,
    backgroundColor: Colors.border,
  },
});
