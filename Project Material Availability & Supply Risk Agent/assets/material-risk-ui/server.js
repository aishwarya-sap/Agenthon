const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const session = require('express-session');
const passport = require('passport');
const xssec = require('@sap/xssec');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;
const AGENT_URL = process.env.AGENT_URL || 'http://localhost:5000';
// UI's own public URL — injected by MTA as ${default-url}. Used for the OAuth2 callback.
const UI_PUBLIC_URL = (process.env.UI_PUBLIC_URL || `http://localhost:${PORT}`).replace(/\/$/, '');

// ---------------------------------------------------------------------------
// XSUAA credentials — read from VCAP_SERVICES (injected by CF when the xsuaa
// service is bound). Absent locally / in mock mode: auth is skipped entirely.
// ---------------------------------------------------------------------------
function getXsuaaCredentials() {
  try {
    const vcap = JSON.parse(process.env.VCAP_SERVICES || '{}');
    const bindings = vcap.xsuaa || [];
    return bindings.length ? bindings[0].credentials : null;
  } catch {
    return null;
  }
}

const xsuaaCreds = getXsuaaCredentials();
if (!xsuaaCreds) {
  console.warn('[auth] No XSUAA binding in VCAP_SERVICES — authentication disabled (dev mode)');
}

// ---------------------------------------------------------------------------
// Session — stores the access token across the OAuth2 redirect flow.
// Set SESSION_SECRET via `cf set-env material-risk-ui SESSION_SECRET <random>`.
// ---------------------------------------------------------------------------
app.use(session({
  secret: process.env.SESSION_SECRET || (() => {
    if (xsuaaCreds) console.warn('[auth] SESSION_SECRET not set — set it via cf set-env');
    return 'dev-only-secret';
  })(),
  resave: false,
  saveUninitialized: false,
  cookie: {
    secure: !!xsuaaCreds,  // HTTPS only in production (CF always HTTPS)
    httpOnly: true,
    maxAge: 3600 * 1000,   // 1 hour, matches XSUAA token-validity in xs-security.json
  },
}));

app.use(passport.initialize());
app.use(passport.session());
passport.serializeUser((user, done) => done(null, user));
passport.deserializeUser((user, done) => done(null, user));

// JWT strategy for programmatic / Joule callers that send a Bearer token directly.
if (xsuaaCreds) {
  passport.use('JWT', new xssec.JWTStrategy(xsuaaCreds));
}

// ---------------------------------------------------------------------------
// Auth middleware: pass session users through; try JWT Bearer for API callers;
// redirect browsers to the XSUAA login page.
// ---------------------------------------------------------------------------
function requireAuth(req, res, next) {
  if (!xsuaaCreds) return next();                         // dev: no binding, skip
  if (req.isAuthenticated()) return next();               // session cookie present

  const authHeader = req.headers['authorization'] || '';
  if (authHeader.toLowerCase().startsWith('bearer ')) {
    // Programmatic caller (Joule, curl, another agent): validate JWT inline.
    return passport.authenticate('JWT', { session: false })(req, res, next);
  }

  // Browser: save the target URL and redirect to XSUAA login.
  req.session.returnTo = req.originalUrl;
  res.redirect('/login');
}

// ---------------------------------------------------------------------------
// Login: redirect browser to XSUAA authorization endpoint (OAuth2 code flow).
// ---------------------------------------------------------------------------
app.get('/login', (req, res) => {
  if (!xsuaaCreds) return res.redirect('/');
  const callbackUri = encodeURIComponent(`${UI_PUBLIC_URL}/login/callback`);
  const loginUrl =
    `${xsuaaCreds.url}/oauth/authorize` +
    `?response_type=code` +
    `&client_id=${encodeURIComponent(xsuaaCreds.clientid)}` +
    `&redirect_uri=${callbackUri}`;
  res.redirect(loginUrl);
});

// ---------------------------------------------------------------------------
// Callback: exchange the authorization code for an access token.
// ---------------------------------------------------------------------------
app.get('/login/callback', async (req, res) => {
  const { code } = req.query;
  if (!code) return res.status(400).send('Missing authorization code');

  try {
    const callbackUri = `${UI_PUBLIC_URL}/login/callback`;
    const tokenRes = await fetch(`${xsuaaCreds.url}/oauth/token`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': 'Basic ' + Buffer.from(
          `${xsuaaCreds.clientid}:${xsuaaCreds.clientsecret}`
        ).toString('base64'),
      },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        code,
        redirect_uri: callbackUri,
      }),
    });

    if (!tokenRes.ok) {
      const detail = await tokenRes.text();
      console.error('[auth] Token exchange failed:', detail);
      return res.status(502).send('Authentication failed — token exchange error');
    }

    const tokenData = await tokenRes.json();
    const user = {
      email: tokenData.user_name || tokenData.email || 'authenticated-user',
      token: tokenData.access_token,
    };
    req.session.accessToken = tokenData.access_token;

    req.login(user, err => {
      if (err) { console.error('[auth] Session login error:', err); return res.status(500).send('Session error'); }
      const returnTo = req.session.returnTo || '/';
      delete req.session.returnTo;
      res.redirect(returnTo);
    });
  } catch (err) {
    console.error('[auth] Token exchange error:', err.message);
    res.status(500).send('Authentication failed');
  }
});

// ---------------------------------------------------------------------------
// Logout: destroy session and redirect to XSUAA global logout.
// ---------------------------------------------------------------------------
app.get('/logout', (req, res) => {
  req.logout(() => {
    req.session.destroy();
    if (xsuaaCreds) {
      const redirectAfterLogout = encodeURIComponent(`${UI_PUBLIC_URL}/login`);
      return res.redirect(`${xsuaaCreds.url}/logout?redirect=${redirectAfterLogout}`);
    }
    res.redirect('/');
  });
});

// ---------------------------------------------------------------------------
// Static assets — served without auth so the login page can load CSS/JS.
// ---------------------------------------------------------------------------
app.use(express.static(path.join(__dirname, 'public')));

// ---------------------------------------------------------------------------
// Protected proxy to the A2A agent.
// Forwards the user's Bearer token so the agent can validate identity.
// ---------------------------------------------------------------------------
app.use('/agent', requireAuth, createProxyMiddleware({
  target: AGENT_URL,
  changeOrigin: true,
  pathRewrite: { '^/agent': '' },
  on: {
    proxyReq: (proxyReq, req) => {
      // Browser session path: token stored in session after OAuth2 code flow.
      // Bearer path: token already in Authorization header (validated by passport).
      const sessionToken = req.session && req.session.accessToken;
      const bearerToken = (req.headers['authorization'] || '').replace(/^bearer /i, '');
      const token = sessionToken || bearerToken;
      if (token) proxyReq.setHeader('Authorization', `Bearer ${token}`);
    },
    error: (err, req, res) => {
      console.error('[proxy] Agent unavailable:', err.message);
      res.status(502).json({ error: 'Agent unavailable', detail: err.message });
    },
  },
}));

// ---------------------------------------------------------------------------
// SPA fallback — all other routes serve index.html (requires auth).
// ---------------------------------------------------------------------------
app.get('*', requireAuth, (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`UI server on port ${PORT}`);
  console.log(`Agent proxy → ${AGENT_URL}`);
  console.log(`XSUAA auth: ${xsuaaCreds ? 'ENABLED' : 'disabled (dev mode)'}`);
});
