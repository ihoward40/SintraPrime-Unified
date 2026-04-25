import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Colors } from '@theme/colors';
import { AIStackParamList } from './types';
import AIAssistantScreen from '@screens/ai/AIAssistantScreen';
import ParliamentScreen from '@screens/ai/ParliamentScreen';

const Stack = createNativeStackNavigator<AIStackParamList>();

export default function AIStack() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: Colors.background },
        animation: 'slide_from_right',
      }}
    >
      <Stack.Screen name="AIAssistant" component={AIAssistantScreen} />
      <Stack.Screen name="Parliament" component={ParliamentScreen} />
    </Stack.Navigator>
  );
}
