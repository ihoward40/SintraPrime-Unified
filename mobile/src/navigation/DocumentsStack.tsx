import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Colors } from '@theme/colors';
import { DocumentsStackParamList } from './types';
import VaultScreen from '@screens/documents/VaultScreen';
import ScannerScreen from '@screens/documents/ScannerScreen';
import DocumentViewerScreen from '@screens/documents/DocumentViewerScreen';

const Stack = createNativeStackNavigator<DocumentsStackParamList>();

export default function DocumentsStack() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: Colors.background },
        animation: 'slide_from_right',
      }}
    >
      <Stack.Screen name="Vault" component={VaultScreen} />
      <Stack.Screen
        name="Scanner"
        component={ScannerScreen}
        options={{ animation: 'slide_from_bottom' }}
      />
      <Stack.Screen name="DocumentViewer" component={DocumentViewerScreen} />
    </Stack.Navigator>
  );
}
