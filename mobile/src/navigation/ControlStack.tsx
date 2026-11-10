/**
 * Control-surface stack navigator.
 *
 * Mirrors the existing *Stack.tsx pattern in mobile/src/navigation:
 * one native stack per feature area, registered from the root navigator.
 *
 * To wire this in:
 *  1. Import ControlStackNavigator in mobile/src/navigation/RootNavigator.tsx
 *     (or MainTabs.tsx) and add it as a screen/tab.
 *  2. Optionally add 'Control' route names to mobile/src/navigation/types.ts.
 *
 * Pattern inspiration: pingdotgg/t3code (MIT).
 * MIT License — see docs/CONTROL_SURFACE.md for attribution.
 */

import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import AgentListScreen from '../control/AgentListScreen';
import RelaySettingsScreen from '../control/RelaySettingsScreen';
import TaskDetailScreen from '../control/TaskDetailScreen';
import type { ControlStackParamList } from '../control/types';

const Stack = createNativeStackNavigator<ControlStackParamList>();

export default function ControlStackNavigator() {
  return (
    <Stack.Navigator initialRouteName="AgentList">
      <Stack.Screen
        name="AgentList"
        component={AgentListScreen}
        options={{ title: 'Agents' }}
      />
      <Stack.Screen
        name="TaskDetail"
        component={TaskDetailScreen}
        options={({ route }) => ({
          title:
            'mode' in route.params && route.params.mode === 'create'
              ? 'New task'
              : 'Task detail',
        })}
      />
      <Stack.Screen
        name="RelaySettings"
        component={RelaySettingsScreen}
        options={{ title: 'Relay settings' }}
      />
    </Stack.Navigator>
  );
}
