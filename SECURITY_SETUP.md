# 🔒 Content Service Security Setup

## 🎯 Current Security Status: EXCELLENT ✅

The statlas-content-service is properly secured with `X-Service-Auth` header authentication.

## 🛡️ Authentication Details

### Required Header
```
X-Service-Auth: <your-service-secret>
```

### Protected Endpoints
- **ALL API endpoints** require authentication
- Only `/health` and `/metrics` are public (for monitoring)

### Security Features
- ✅ Constant-time comparison (prevents timing attacks)
- ✅ CORS properly configured
- ✅ OPTIONS requests handled correctly

## 🔧 Production Deployment

### 1. Generate Strong Service Secret
```bash
# Generate a strong 32-character secret
openssl rand -hex 32
```

### 2. Deploy with Secret
```bash
# Deploy to Cloud Run with service secret
gcloud run deploy statlas-content-service \
  --image $IMAGE_URI \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_CLOUD_PROJECT=statlas-467715 \
  --set-env-vars SERVICE_SECRET=<your-generated-secret> \
  --set-env-vars CDN_BASE_URL=https://cdn.statlas.app
```

### 3. Share Secret with Authorized Services

**Services that need access:**
- **statlas-core-service** (main backend)
- **statlas-web-app** (frontend - if direct access needed)

**Add to their environment:**
```bash
CONTENT_SERVICE_SECRET=<your-generated-secret>
CONTENT_SERVICE_URL=https://statlas-content-service-<hash>-uc.a.run.app
```

## 🧪 Testing Authentication

### Valid Request
```bash
curl -H "X-Service-Auth: your-secret" \
  https://your-service-url/countries/bulk
# Returns: 200 OK with data
```

### Invalid Request
```bash
curl https://your-service-url/countries/bulk
# Returns: 401 Unauthorized - "Missing X-Service-Auth header"
```

### Wrong Secret
```bash
curl -H "X-Service-Auth: wrong-secret" \
  https://your-service-url/countries/bulk
# Returns: 401 Unauthorized - "Invalid service authentication"
```

## 🌐 Frontend Integration

### JavaScript Example
```javascript
const response = await fetch('https://your-content-service/countries/bulk', {
  headers: {
    'X-Service-Auth': process.env.CONTENT_SERVICE_SECRET
  }
});
```

### Environment Variables for Frontend
```bash
# For statlas-web-app
NEXT_PUBLIC_CONTENT_SERVICE_URL=https://your-service-url
CONTENT_SERVICE_SECRET=<your-secret>  # Server-side only!
```

## 🚨 Security Best Practices

### ✅ DO
- Store secrets in environment variables
- Use different secrets for dev/staging/production
- Rotate secrets periodically
- Keep secrets server-side only (never in client code)

### ❌ DON'T
- Hardcode secrets in source code
- Share secrets in plain text
- Use weak/predictable secrets
- Expose secrets in client-side code

## 🔄 Secret Rotation

1. **Generate new secret**
2. **Update Cloud Run environment**
3. **Update all consuming services**
4. **Verify all services working**
5. **Monitor for authentication errors**

---

## ✅ Current Status

- 🔒 **Authentication:** Implemented and working
- 🌐 **CORS:** Properly configured
- 🚀 **Deployment:** Ready for production
- 🔑 **Secret:** Needs production value
