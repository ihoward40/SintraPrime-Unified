import { NavigatorScreenParams } from '@react-navigation/native';

// Auth Stack
export type AuthStackParamList = {
  Splash: undefined;
  Login: undefined;
  Biometric: { userId: string; method: 'faceid' | 'touchid' | 'pin' };
  ForgotPassword: undefined;
};

// Legal Stack
export type LegalStackParamList = {
  LegalHub: undefined;
  CaseDetail: { caseId: string; caseTitle: string };
  MotionDrafter: { caseId?: string; motionType?: string };
  TrustLaw: undefined;
  CaseLawSearch: { query?: string };
  NewCase: undefined;
};

// Financial Stack
export type FinancialStackParamList = {
  Financial: undefined;
  Accounts: undefined;
  CreditScore: undefined;
  Budget: undefined;
  Funding: { category?: string };
  TransactionDetail: { transactionId: string };
};

// Documents Stack
export type DocumentsStackParamList = {
  Vault: undefined;
  Scanner: { caseId?: string };
  DocumentViewer: { documentId: string; documentTitle: string; uri: string };
  DocumentUpload: { caseId?: string };
};

// AI Stack
export type AIStackParamList = {
  AIAssistant: { initialQuery?: string };
  Parliament: undefined;
  ConversationHistory: undefined;
};

// Settings Stack
export type SettingsStackParamList = {
  Settings: undefined;
  Notifications: undefined;
  Security: undefined;
  Profile: undefined;
  Subscription: undefined;
  About: undefined;
};

// Main Tab Navigator
export type MainTabParamList = {
  Home: undefined;
  Legal: NavigatorScreenParams<LegalStackParamList>;
  Financial: NavigatorScreenParams<FinancialStackParamList>;
  Documents: NavigatorScreenParams<DocumentsStackParamList>;
  AI: NavigatorScreenParams<AIStackParamList>;
  Settings: NavigatorScreenParams<SettingsStackParamList>;
};

// Root Navigator
export type RootStackParamList = {
  Auth: NavigatorScreenParams<AuthStackParamList>;
  Main: NavigatorScreenParams<MainTabParamList>;
  Modal: { screen: string; params?: object };
};

declare global {
  namespace ReactNavigation {
    interface RootParamList extends RootStackParamList {}
  }
}
