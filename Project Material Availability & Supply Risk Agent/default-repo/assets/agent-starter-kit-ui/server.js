const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3000;                       // CF injects $PORT; never hardcode
const AGENT_URL = process.env.AGENT_URL || 'http://localhost:5000'; // MTA injects the deployed agent URL

app.use(express.static(path.join(__dirname, 'public')));

// Proxy /agent/* to the A2A agent. pathRewrite strips the /agent prefix.
app.use('/agent', createProxyMiddleware({
  target: AGENT_URL,
  changeOrigin: true,
  pathRewrite: { '^/agent': '' },
  on: {
    error: (err, req, res) => {
      console.error('Proxy error:', err.message);
      res.status(502).json({ error: 'Agent unavailable', detail: err.message });
    }
  }
}));

// SPA fallback
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(PORT, () => {
  console.log(`UI server running on port ${PORT}`);
  console.log(`Proxying agent requests to ${AGENT_URL}`);
});
