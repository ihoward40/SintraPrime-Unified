# SintraPrime Mobile App — App Store Submission Guide

## Prerequisites

- Apple Developer Account (enrolled in Apple Developer Program)
- Google Play Developer Account
- EAS CLI installed: `npm install -g eas-cli`
- Expo account: `eas login`

---

## 1. Environment Setup

```bash
cd mobile/
npm install
eas login
eas build:configure
```

---

## 2. iOS App Store Submission

### Step 1: Configure App Store Connect
1. Go to [App Store Connect](https://appstoreconnect.apple.com)
2. Create a new app with Bundle ID: `com.ikesolutions.sintraprime`
3. Fill in app metadata (name, description, keywords, screenshots)
4. Set pricing to Free

### Step 2: Build for iOS Production
```bash
eas build --platform ios --profile production
```

### Step 3: Submit to App Store
```bash
eas submit --platform ios --profile production
```

### Step 4: App Review Checklist
- [ ] Privacy policy URL added
- [ ] Support URL added
- [ ] Age rating configured (17+ for legal content)
- [ ] Export compliance: Uses encryption? (HTTPS = yes, standard exemption applies)
- [ ] App screenshots for all required device sizes
- [ ] App preview video (optional but recommended)

---

## 3. Google Play Store Submission

### Step 1: Configure Google Play Console
1. Go to [Google Play Console](https://play.google.com/console)
2. Create a new app
3. Complete store listing (title, description, screenshots)

### Step 2: Service Account Setup
1. Create a service account in Google Cloud Console
2. Grant access in Play Console → Setup → API Access
3. Download key as `google-service-account.json` (DO NOT commit to git)

### Step 3: Build Android AAB
```bash
eas build --platform android --profile production
```

### Step 4: Submit to Play Store
```bash
eas submit --platform android --profile production
```

### Step 5: Play Store Checklist
- [ ] Content rating questionnaire completed
- [ ] Privacy policy URL added
- [ ] Data safety section completed
- [ ] Target audience: 18+ (legal app)
- [ ] Store listing assets (feature graphic, screenshots)

---

## 4. Over-the-Air Updates (OTA)

For JS-only updates without full store review:
```bash
eas update --branch production --message "Bug fix: voice input"
```

---

## 5. Environment Variables

Set in Expo dashboard or `.env.local`:
```
EXPO_PUBLIC_API_URL=https://api.sintraprime.ikesolutions.org
EXPO_PUBLIC_LOCAL_LLM=false
```

---

## 6. Development Builds

```bash
# iOS Simulator
eas build --platform ios --profile development
# Install on device
eas build --platform android --profile preview
```

---

## 7. Troubleshooting

| Issue | Solution |
|-------|----------|
| Build fails on iOS | Check `ios.bundleIdentifier` matches App Store Connect |
| Microphone rejected | Ensure `NSMicrophoneUsageDescription` is in `app.json` |
| Android permissions | Verify `RECORD_AUDIO` in android.permissions |
| OTA update not loading | Check `extra.eas.projectId` matches EAS dashboard |

---

## 8. Production Checklist

- [ ] API URL points to production backend (not localhost)
- [ ] Biometric auth tested on real devices
- [ ] Voice input tested on iOS and Android
- [ ] All legal categories return correct responses
- [ ] Offline mode gracefully handled
- [ ] Error messages are user-friendly
- [ ] Analytics/crash reporting configured (Sentry recommended)
- [ ] Deep links configured for legal document sharing
