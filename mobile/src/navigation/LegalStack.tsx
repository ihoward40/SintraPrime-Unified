import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Colors } from '@theme/colors';
import { LegalStackParamList } from './types';
import LegalHubScreen from '@screens/legal/LegalHubScreen';
import CaseDetailScreen from '@screens/legal/CaseDetailScreen';
import MotionDrafterScreen from '@screens/legal/MotionDrafterScreen';
import TrustLawScreen from '@screens/legal/TrustLawScreen';
import CaseLawSearchScreen from '@screens/legal/CaseLawSearchScreen';

const Stack = createNativeStackNavigator<LegalStackParamList>();

export default function LegalStack() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: Colors.background },
        animation: 'slide_from_right',
      }}
    >
      <Stack.Screen name="LegalHub" component={LegalHubScreen} />
      <Stack.Screen name="CaseDetail" component={CaseDetailScreen} />
      <Stack.Screen name="MotionDrafter" component={MotionDrafterScreen} />
      <Stack.Screen name="TrustLaw" component={TrustLawScreen} />
      <Stack.Screen name="CaseLawSearch" component={CaseLawSearchScreen} />
    </Stack.Navigator>
  );
}
