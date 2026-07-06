# M3 Login Page Plan

**Goal:** Add a real `/login` page to the Vite frontend so the Document Vault and future M3 pages can authenticate with the live backend instead of relying on the mock `Marcus A. Sintra` user.

**Status:** Investigation complete. Ready to implement.

---

## Current State

### Backend (ready)
- `POST /api/v1/auth/login` accepts `{ email, password, mfa_code? }`
- Returns `{ access_token, token_type, expires_in, user_id, role, tenant_id }`
- Sets `refresh_token` as `httpOnly` cookie on `/api/v1/auth`
- Invalid credentials → `401`; locked/deactivated accounts → `423`/`403`

### Frontend (broken for real auth)
- `api/client.ts` reads `localStorage.getItem('sintraprime_token')` and attaches `Authorization: Bearer ***`
- On `401`, it redirects to `/login` — **but that route does not exist**
- `useAppStore` starts with `isAuthenticated: true` and a hardcoded mock user
- `App.tsx` has no `/login` route
- DocumentVault fetches real documents but silently falls back to mock data on any error

---

## Implementation Plan

### 1. New File: `web/src/pages/Login.tsx`

A self-contained login page using existing UI primitives (`Button`, `Card`, `LoadingSpinner`).

**Behavior:**
- Controlled form: email, password
- Submit calls `POST /api/v1/auth/login` via `api.post`
- On success:
  - `localStorage.setItem('sintraprime_token', access_token)`
  - `localStorage.setItem('sintraprime_refresh_token', 'cookie-managed')` — placeholder so client refresh path sees a token; actual refresh uses the httpOnly cookie
  - `useAppStore.setUser({ id: user_id, name: email, email, role, ... })`
  - Navigate to `/dashboard` or `/documents`
- On failure: show inline error message
- Loading state disables button

**Design:**
- Centered card on dark background
- Gold primary button matching brand
- Link to password reset (future)

### 2. Update `web/src/App.tsx`

Add a public `/login` route **outside** `<Layout>` so the sidebar/header are hidden:

```tsx
<Routes>
  <Route path="/login" element={<Login />} />
  <Route path="/" element={<Layout />}>
    {/* existing protected routes */}
  </Route>
</Routes>
```

### 3. Update `web/src/store/appStore.ts`

Change initial state:
- `user: null`
- `isAuthenticated: false`
- Keep `defaultIntegrations` and `defaultNotifications` only for authenticated demo? Better: clear them or keep empty; mock data should not appear for unauthenticated users.

Add `login` action:
```ts
login: (accessToken, user) => {
  localStorage.setItem('sintraprime_token', accessToken);
  set({ user, isAuthenticated: true });
}
```

Keep existing `logout` action (already clears token + redirects).

### 4. Update `web/src/api/client.ts`

Fix the refresh flow. Currently it sends `refresh_token` in the request body, but the backend expects it as an `httpOnly` cookie at `/api/v1/auth/refresh`. Change to:

```ts
const response = await axios.post(`${BASE_URL}/api/${API_VERSION}/auth/refresh`, {}, { withCredentials: true });
```

Also add `withCredentials: true` to the main axios instance so login sets/receives cookies.

### 5. Update `web/src/pages/DocumentVault.tsx`

Small improvements to make E2E possible later:
- Remove silent mock fallback — show explicit error instead
- Add `data-testid` attributes to export result fields so Playwright can assert them
- Keep the real API call path

Specific test IDs:
- `data-testid="export-result"`
- `data-testid="snapshot-id"`
- `data-testid="packet-hash"`
- `data-testid="audit-id"`
- `data-testid="evidence-hash"`

### 6. Add Unit Test: `web/src/pages/__tests__/Login.test.tsx`

Use `vitest` + `@testing-library/react` (already in `web/package.json`? verify first).

Test cases:
- Renders email/password inputs
- Shows error on failed login
- Calls `navigate` on successful login
- Stores token in `localStorage`

If test deps are missing, install them:
```bash
npm install -D @testing-library/react @testing-library/jest-dom @testing-library/user-event vitest jsdom
```

### 7. Verification Steps

| Check | Command / Action |
|-------|------------------|
| Type check | `cd web && npx tsc --noEmit` |
| Lint | `cd web && npm run lint` (if script exists) or `npx eslint src/pages/Login.tsx` |
| Unit test | `cd web && npx vitest run src/pages/__tests__/Login.test.tsx` |
| Manual smoke | Start Vite dev server, visit `/login`, log in with seeded E2E user, confirm redirect |

---

## Files to Modify / Create

| Path | Action |
|------|--------|
| `web/src/pages/Login.tsx` | Create |
| `web/src/App.tsx` | Add `/login` route |
| `web/src/store/appStore.ts` | Start unauthenticated; add `login` action |
| `web/src/api/client.ts` | Enable `withCredentials`; fix refresh endpoint call |
| `web/src/pages/DocumentVault.tsx` | Add test IDs; remove silent mock fallback |
| `web/src/pages/__tests__/Login.test.tsx` | Create |
| `web/package.json` | Add vitest/test scripts if missing |

---

## Out of Scope (for this PR)

- MFA flow (handled by backend; UI can add TOTP input later)
- Password reset UI
- Full route guards / protected redirects (can be added in follow-up)
- Playwright E2E (remains PR #153)

---

## Estimated Effort

- Implementation: ~30 minutes
- Tests + verification: ~15 minutes
- Total: **~45 minutes**

---

## Next Action

Implement the above as a focused PR (likely **PR #153** since the Playwright work is still draft), or split into:
- **PR #153:** Login page + auth wiring
- **PR #154:** Playwright E2E (built on top of PR #153)

Recommend proceeding with PR #153 as the login page — it unblocks real E2E and makes the Document Vault truly usable.
