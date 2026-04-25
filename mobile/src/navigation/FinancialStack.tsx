import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Colors } from '@theme/colors';
import { FinancialStackParamList } from './types';
import FinancialScreen from '@screens/financial/FinancialScreen';
import AccountsScreen from '@screens/financial/AccountsScreen';
import CreditScoreScreen from '@screens/financial/CreditScoreScreen';
import BudgetScreen from '@screens/financial/BudgetScreen';
import FundingScreen from '@screens/financial/FundingScreen';

const Stack = createNativeStackNavigator<FinancialStackParamList>();

export default function FinancialStack() {
  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: Colors.background },
        animation: 'slide_from_right',
      }}
    >
      <Stack.Screen name="Financial" component={FinancialScreen} />
      <Stack.Screen name="Accounts" component={AccountsScreen} />
      <Stack.Screen name="CreditScore" component={CreditScoreScreen} />
      <Stack.Screen name="Budget" component={BudgetScreen} />
      <Stack.Screen name="Funding" component={FundingScreen} />
    </Stack.Navigator>
  );
}
