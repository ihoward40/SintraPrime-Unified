import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useRoute } from '@react-navigation/native';
import { Send, Mic, BookmarkPlus, Sparkles, Users } from 'lucide-react-native';
import { LinearGradient } from 'expo-linear-gradient';
import * as Haptics from 'expo-haptics';
import { useNavigation } from '@react-navigation/native';
import { Colors } from '@theme/colors';
import { Typography } from '@theme/typography';
import { Spacing, BorderRadius } from '@theme/spacing';
import ChatBubble, { ChatMessage } from '@components/ai/ChatBubble';
import TypingIndicator from '@components/ai/TypingIndicator';
import AgentAvatar from '@components/ai/AgentAvatar';

const SUGGESTED_QUERIES = [
  'What are my rights in a wrongful termination case?',
  'How can I improve my credit score fast?',
  'Explain the difference between a will and a trust.',
  'What SBA loans qualify for my business?',
  'Draft a cease and desist letter template.',
];

const MOCK_AI_RESPONSE = `Based on your current legal situation and financial profile, here's my analysis:

**Regarding wrongful termination:**
Under Title VII and applicable state law, you have strong grounds for a discrimination claim. The key elements are:

1. **Protected class membership** — Established ✓
2. **Qualified for the position** — Established ✓  
3. **Adverse employment action** — Established ✓
4. **Discriminatory intent** — Evidence suggests this ✓

**Recommended next steps:**
- File an EEOC charge within 180 days of termination
- Preserve all communications and performance reviews
- Consider filing a motion for summary judgment

**Sources:**
1. McDonnell Douglas Corp. v. Green, 411 U.S. 792 (1973)
2. Title VII of the Civil Rights Act of 1964, 42 U.S.C. § 2000e

*Disclaimer: This is AI legal information, not legal advice. Consult a licensed attorney before taking legal action.*`;

let msgCounter = 0;
function newMsg(role: ChatMessage['role'], content: string, agentName?: string): ChatMessage {
  return {
    id: `msg-${++msgCounter}`,
    role,
    content,
    timestamp: new Date(),
    agentName,
    citations: role === 'assistant' ? ['McDonnell Douglas Corp. v. Green, 411 U.S. 792 (1973)', 'Title VII, 42 U.S.C. § 2000e'] : undefined,
  };
}

export default function AIAssistantScreen() {
  const route = useRoute<any>();
  const navigation = useNavigation<any>();
  const initialQuery = route.params?.initialQuery;

  const [messages, setMessages] = useState<ChatMessage[]>([
    newMsg('assistant', 'Hello! I am your SintraPrime AI Counsel. I can help with legal questions, financial planning, case strategy, and more. What can I help you with today?', 'SintraPrime AI'),
  ]);
  const [input, setInput] = useState(initialQuery ?? '');
  const [isTyping, setIsTyping] = useState(false);
  const flatListRef = useRef<FlatList>(null);

  useEffect(() => {
    if (initialQuery) {
      handleSend(initialQuery);
    }
  }, []);

  const handleSend = useCallback(async (text?: string) => {
    const msgText = text ?? input.trim();
    if (!msgText) return;

    const userMsg = newMsg('user', msgText);
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsTyping(true);
    await Haptics.selectionAsync();

    // Scroll to bottom
    setTimeout(() => flatListRef.current?.scrollToEnd({ animated: true }), 100);

    // Simulate AI response
    await new Promise((r) => setTimeout(r, 2000 + Math.random() * 1000));
    setIsTyping(false);

    const aiMsg = newMsg('assistant', MOCK_AI_RESPONSE, 'SintraPrime Legal AI');
    setMessages((prev) => [...prev, aiMsg]);
    setTimeout(() => flatListRef.current?.scrollToEnd({ animated: true }), 100);
    await Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
  }, [input]);

  const handleSave = (message: ChatMessage) => {
    // Save to vault
  };

  return (
    <View style={styles.container}>
      {/* Header */}
      <LinearGradient
        colors={[Colors.navy[950], Colors.navy[900]]}
        style={styles.header}
      >
        <SafeAreaView edges={['top']}>
          <View style={styles.headerContent}>
            <AgentAvatar name="AI" animated={isTyping} size="md" />
            <View style={styles.headerText}>
              <Text style={styles.headerTitle}>AI Counsel</Text>
              <Text style={styles.headerSub}>
                {isTyping ? 'Thinking...' : 'Ready to help'}
              </Text>
            </View>
            <TouchableOpacity
              onPress={() => navigation.navigate('Parliament')}
              style={styles.parliamentBtn}
            >
              <Users size={18} color={Colors.gold[500]} strokeWidth={1.5} />
            </TouchableOpacity>
          </View>
        </SafeAreaView>
      </LinearGradient>

      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={0}
      >
        {/* Messages */}
        <FlatList
          ref={flatListRef}
          data={messages}
          keyExtractor={(item) => item.id}
          renderItem={({ item }) => (
            <ChatBubble message={item} onSave={handleSave} />
          )}
          contentContainerStyle={styles.messageList}
          ListFooterComponent={isTyping ? <TypingIndicator /> : null}
          onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
          showsVerticalScrollIndicator={false}
        />

        {/* Suggestions (only if no conversation) */}
        {messages.length <= 1 && (
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.suggestions}
          >
            {SUGGESTED_QUERIES.map((q) => (
              <TouchableOpacity
                key={q}
                onPress={() => handleSend(q)}
                style={styles.suggestionChip}
              >
                <Sparkles size={12} color={Colors.gold[500]} strokeWidth={1.5} />
                <Text style={styles.suggestionText} numberOfLines={2}>{q}</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        )}

        {/* Input */}
        <SafeAreaView edges={['bottom']} style={styles.inputContainer}>
          <View style={styles.inputRow}>
            <TouchableOpacity style={styles.micBtn}>
              <Mic size={18} color={Colors.textMuted} strokeWidth={1.5} />
            </TouchableOpacity>
            <TextInput
              style={styles.input}
              value={input}
              onChangeText={setInput}
              placeholder="Ask your AI counsel..."
              placeholderTextColor={Colors.textMuted}
              multiline
              maxLength={2000}
              returnKeyType="send"
              onSubmitEditing={() => handleSend()}
            />
            <TouchableOpacity
              onPress={() => handleSend()}
              style={[styles.sendBtn, !input.trim() && styles.sendBtnDisabled]}
              disabled={!input.trim() || isTyping}
            >
              <Send size={18} color={input.trim() ? Colors.navy[900] : Colors.textMuted} strokeWidth={2} />
            </TouchableOpacity>
          </View>
        </SafeAreaView>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: Colors.background },
  header: {
    paddingHorizontal: Spacing.base,
    paddingBottom: Spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  headerContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.md,
    paddingTop: Spacing.md,
  },
  headerText: { flex: 1 },
  headerTitle: { ...Typography.titleMedium, color: Colors.textPrimary },
  headerSub: { ...Typography.bodySmall, color: Colors.textMuted },
  parliamentBtn: {
    width: 36, height: 36, borderRadius: 12,
    backgroundColor: Colors.surface,
    alignItems: 'center', justifyContent: 'center',
    borderWidth: 1, borderColor: Colors.border,
  },
  messageList: { paddingTop: Spacing.base, paddingBottom: Spacing.sm },
  suggestions: {
    paddingHorizontal: Spacing.base,
    paddingVertical: Spacing.sm,
    gap: Spacing.sm,
  },
  suggestionChip: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: Spacing.xs,
    maxWidth: 200,
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.xl,
    padding: Spacing.md,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  suggestionText: { ...Typography.bodySmall, color: Colors.textSecondary, flex: 1, lineHeight: 18 },
  inputContainer: {
    borderTopWidth: 1,
    borderTopColor: Colors.border,
    backgroundColor: Colors.navy[950],
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: Spacing.sm,
    padding: Spacing.md,
  },
  micBtn: {
    width: 40, height: 40,
    borderRadius: 20,
    backgroundColor: Colors.surface,
    alignItems: 'center', justifyContent: 'center',
    borderWidth: 1, borderColor: Colors.border,
  },
  input: {
    flex: 1,
    ...Typography.bodyMedium,
    color: Colors.textPrimary,
    backgroundColor: Colors.surface,
    borderRadius: BorderRadius.xl,
    paddingHorizontal: Spacing.base,
    paddingVertical: Spacing.md,
    maxHeight: 120,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  sendBtn: {
    width: 40, height: 40,
    borderRadius: 20,
    backgroundColor: Colors.gold[500],
    alignItems: 'center', justifyContent: 'center',
  },
  sendBtnDisabled: {
    backgroundColor: Colors.border,
  },
});
