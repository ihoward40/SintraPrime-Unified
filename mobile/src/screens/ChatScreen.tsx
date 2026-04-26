import React, { useState, useRef, useCallback, useEffect } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  FlatList,
  StyleSheet,
  Alert,
  Share,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  SafeAreaView,
} from 'react-native';
import * as Clipboard from 'expo-clipboard';
import { Audio } from 'expo-av';
import { useSintraAPI } from '../hooks/useSintraAPI';

type LegalCategory = 'trust' | 'legal' | 'banking' | 'federal';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: string[];
  timestamp: Date;
}

const CATEGORIES: { label: string; value: LegalCategory; color: string }[] = [
  { label: 'Trust', value: 'trust', color: '#6366f1' },
  { label: 'Legal', value: 'legal', color: '#0ea5e9' },
  { label: 'Banking', value: 'banking', color: '#22c55e' },
  { label: 'Federal', value: 'federal', color: '#f59e0b' },
];

export default function ChatScreen() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<LegalCategory>('legal');
  const [jurisdiction, setJurisdiction] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [recording, setRecording] = useState<Audio.Recording | null>(null);
  const flatListRef = useRef<FlatList>(null);
  const { ask, loading, error } = useSintraAPI();

  useEffect(() => {
    if (error) {
      Alert.alert('Error', error);
    }
  }, [error]);

  const sendMessage = useCallback(async () => {
    if (!inputText.trim() || loading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputText.trim(),
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    const questionText = inputText.trim();
    setInputText('');

    const response = await ask({
      question: questionText,
      category: selectedCategory,
      jurisdiction: jurisdiction || undefined,
    });

    if (response) {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: (response.answer as string) || (response.response as string) || JSON.stringify(response),
        citations: response.citations as string[] | undefined,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, assistantMessage]);
    }

    setTimeout(() => flatListRef.current?.scrollToEnd({ animated: true }), 100);
  }, [inputText, loading, ask, selectedCategory, jurisdiction]);

  const startRecording = async () => {
    try {
      const { granted } = await Audio.requestPermissionsAsync();
      if (!granted) {
        Alert.alert('Permission required', 'Microphone access is needed for voice input.');
        return;
      }
      await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true });
      const { recording: rec } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      setRecording(rec);
      setIsRecording(true);
    } catch (e) {
      Alert.alert('Error', 'Could not start recording');
    }
  };

  const stopRecording = async () => {
    if (!recording) return;
    setIsRecording(false);
    await recording.stopAndUnloadAsync();
    const uri = recording.getURI();
    setRecording(null);
    if (uri) {
      // In production: send to speech-to-text API
      Alert.alert('Voice recorded', 'Voice transcription would process: ' + uri);
    }
  };

  const copyToClipboard = async (text: string) => {
    await Clipboard.setStringAsync(text);
    Alert.alert('Copied', 'Response copied to clipboard');
  };

  const shareMessage = async (text: string) => {
    await Share.share({ message: text, title: 'SintraPrime Legal Response' });
  };

  const renderMessage = ({ item }: { item: Message }) => (
    <View style={[styles.messageBubble, item.role === 'user' ? styles.userBubble : styles.assistantBubble]}>
      <Text style={styles.messageRole}>{item.role === 'user' ? 'You' : 'SintraPrime'}</Text>
      <Text style={styles.messageText}>{item.content}</Text>
      {item.citations && item.citations.length > 0 && (
        <View style={styles.citationsContainer}>
          <Text style={styles.citationsTitle}>Citations:</Text>
          {item.citations.map((citation, index) => (
            <Text key={index} style={styles.citation}>• {citation}</Text>
          ))}
        </View>
      )}
      {item.role === 'assistant' && (
        <View style={styles.messageActions}>
          <TouchableOpacity onPress={() => copyToClipboard(item.content)} style={styles.actionButton}>
            <Text style={styles.actionButtonText}>Copy</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={() => shareMessage(item.content)} style={styles.actionButton}>
            <Text style={styles.actionButtonText}>Share</Text>
          </TouchableOpacity>
        </View>
      )}
    </View>
  );

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>SintraPrime</Text>
        <Text style={styles.headerSubtitle}>AI Legal Assistant</Text>
      </View>

      {/* Category Selector */}
      <View style={styles.categoryRow}>
        {CATEGORIES.map(cat => (
          <TouchableOpacity
            key={cat.value}
            style={[styles.categoryButton, selectedCategory === cat.value && { backgroundColor: cat.color }]}
            onPress={() => setSelectedCategory(cat.value)}
          >
            <Text style={[styles.categoryText, selectedCategory === cat.value && styles.categoryTextActive]}>
              {cat.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Jurisdiction Input */}
      <TextInput
        style={styles.jurisdictionInput}
        placeholder="Jurisdiction (e.g., California, Federal)"
        placeholderTextColor="#64748b"
        value={jurisdiction}
        onChangeText={setJurisdiction}
      />

      {/* Messages */}
      <KeyboardAvoidingView style={styles.flex} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <FlatList
          ref={flatListRef}
          data={messages}
          renderItem={renderMessage}
          keyExtractor={item => item.id}
          style={styles.messageList}
          contentContainerStyle={styles.messageListContent}
          ListEmptyComponent={
            <View style={styles.emptyState}>
              <Text style={styles.emptyStateText}>Ask SintraPrime a legal question</Text>
              <Text style={styles.emptyStateSubtext}>Trust law, banking regulations, federal statutes, and more</Text>
            </View>
          }
        />

        {loading && (
          <View style={styles.loadingRow}>
            <ActivityIndicator color="#6366f1" />
            <Text style={styles.loadingText}>SintraPrime is thinking...</Text>
          </View>
        )}

        {/* Input Row */}
        <View style={styles.inputRow}>
          <TouchableOpacity
            style={[styles.voiceButton, isRecording && styles.voiceButtonActive]}
            onPress={isRecording ? stopRecording : startRecording}
          >
            <Text style={styles.voiceButtonText}>{isRecording ? '⏹' : '🎤'}</Text>
          </TouchableOpacity>
          <TextInput
            style={styles.textInput}
            placeholder="Ask a legal question..."
            placeholderTextColor="#64748b"
            value={inputText}
            onChangeText={setInputText}
            multiline
            returnKeyType="send"
            onSubmitEditing={sendMessage}
          />
          <TouchableOpacity style={styles.sendButton} onPress={sendMessage} disabled={loading || !inputText.trim()}>
            <Text style={styles.sendButtonText}>Send</Text>
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0f172a' },
  flex: { flex: 1 },
  header: { padding: 16, borderBottomWidth: 1, borderBottomColor: '#1e293b' },
  headerTitle: { fontSize: 22, fontWeight: 'bold', color: '#f1f5f9' },
  headerSubtitle: { fontSize: 13, color: '#64748b', marginTop: 2 },
  categoryRow: { flexDirection: 'row', padding: 12, gap: 8 },
  categoryButton: {
    flex: 1, paddingVertical: 8, borderRadius: 8,
    backgroundColor: '#1e293b', alignItems: 'center',
  },
  categoryText: { color: '#94a3b8', fontSize: 13, fontWeight: '600' },
  categoryTextActive: { color: '#fff' },
  jurisdictionInput: {
    marginHorizontal: 12, marginBottom: 8, padding: 10,
    backgroundColor: '#1e293b', color: '#f1f5f9',
    borderRadius: 8, fontSize: 14,
  },
  messageList: { flex: 1 },
  messageListContent: { padding: 12, gap: 12 },
  messageBubble: { padding: 14, borderRadius: 12, maxWidth: '90%' },
  userBubble: { backgroundColor: '#1e40af', alignSelf: 'flex-end' },
  assistantBubble: { backgroundColor: '#1e293b', alignSelf: 'flex-start' },
  messageRole: { fontSize: 11, color: '#94a3b8', marginBottom: 4, fontWeight: '600' },
  messageText: { color: '#f1f5f9', fontSize: 15, lineHeight: 22 },
  citationsContainer: { marginTop: 10, paddingTop: 8, borderTopWidth: 1, borderTopColor: '#334155' },
  citationsTitle: { color: '#94a3b8', fontSize: 12, fontWeight: '600', marginBottom: 4 },
  citation: { color: '#64748b', fontSize: 12, lineHeight: 18 },
  messageActions: { flexDirection: 'row', marginTop: 10, gap: 8 },
  actionButton: { paddingHorizontal: 12, paddingVertical: 6, backgroundColor: '#334155', borderRadius: 6 },
  actionButtonText: { color: '#94a3b8', fontSize: 12 },
  loadingRow: { flexDirection: 'row', alignItems: 'center', padding: 12, gap: 8 },
  loadingText: { color: '#64748b', fontSize: 14 },
  inputRow: { flexDirection: 'row', padding: 12, gap: 8, alignItems: 'flex-end', borderTopWidth: 1, borderTopColor: '#1e293b' },
  voiceButton: { width: 44, height: 44, borderRadius: 22, backgroundColor: '#1e293b', justifyContent: 'center', alignItems: 'center' },
  voiceButtonActive: { backgroundColor: '#dc2626' },
  voiceButtonText: { fontSize: 20 },
  textInput: { flex: 1, backgroundColor: '#1e293b', color: '#f1f5f9', borderRadius: 10, padding: 10, fontSize: 15, maxHeight: 120 },
  sendButton: { paddingHorizontal: 16, paddingVertical: 10, backgroundColor: '#6366f1', borderRadius: 10 },
  sendButtonText: { color: '#fff', fontWeight: '600' },
  emptyState: { alignItems: 'center', paddingTop: 60, paddingHorizontal: 32 },
  emptyStateText: { color: '#f1f5f9', fontSize: 18, fontWeight: '600', textAlign: 'center', marginBottom: 8 },
  emptyStateSubtext: { color: '#64748b', fontSize: 14, textAlign: 'center', lineHeight: 20 },
});
