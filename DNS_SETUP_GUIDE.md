# 🌐 Complete DNS Setup Guide for statlas.app

## 🎯 Overview

You need to configure DNS records to point your domain to your application hosting platform. Here's the complete setup for all subdomains.

## 🏗️ Application Architecture Plan

```
statlas.app              → Main web application
www.statlas.app          → Redirect to statlas.app
cdn.statlas.app          → Flag assets & static content
api.statlas.app          → API endpoints (optional)
```

## 📋 DNS Records to Add in Cloudflare

**Go to Cloudflare Dashboard → statlas.app → DNS → Records**

### 1. Main Application Domain

**Where is your main application hosted?**

#### Option A: Vercel (Recommended for Next.js/React)
```
Type: CNAME
Name: @
Target: cname.vercel-dns.com
Proxy: 🟠 Proxied
```

#### Option B: Netlify
```
Type: CNAME  
Name: @
Target: your-site-name.netlify.app
Proxy: 🟠 Proxied
```

#### Option C: Google Cloud Run
```
Type: A
Name: @
Target: [Cloud Run IP - get from gcloud]
Proxy: 🟠 Proxied
```

#### Option D: Custom Server/VPS
```
Type: A
Name: @
Target: [Your server IP address]
Proxy: 🟠 Proxied
```

### 2. WWW Subdomain (Redirect)
```
Type: CNAME
Name: www
Target: statlas.app
Proxy: 🟠 Proxied
```

### 3. CDN Subdomain (Flag Assets)
```
Type: CNAME
Name: cdn
Target: statlas-flag-assets.storage.googleapis.com
Proxy: 🟠 Proxied
```

### 4. API Subdomain (Optional)
```
Type: CNAME
Name: api
Target: [Your API hosting target]
Proxy: 🟠 Proxied
```

## 🔧 Cloudflare Configuration

### SSL/TLS Settings
**Cloudflare Dashboard → statlas.app → SSL/TLS:**

1. **Overview:**
   - Encryption mode: **Full (strict)**

2. **Edge Certificates:**
   - Always Use HTTPS: **On**
   - Minimum TLS Version: **1.2**
   - Automatic HTTPS Rewrites: **On**

### Page Rules (Optional Performance Boost)
**Cloudflare Dashboard → statlas.app → Rules → Page Rules:**

1. **Static Assets Caching:**
   ```
   URL: cdn.statlas.app/flags/*
   Settings:
   - Cache Level: Cache Everything
   - Browser Cache TTL: 1 year
   - Edge Cache TTL: 1 month
   ```

2. **WWW Redirect:**
   ```
   URL: www.statlas.app/*
   Settings:
   - Forwarding URL: 301 Redirect
   - Destination: https://statlas.app/$1
   ```

## 🧪 Testing Your Setup

After adding DNS records, test with:

```bash
# Test main domain
curl -I https://statlas.app

# Test www redirect  
curl -I https://www.statlas.app

# Test CDN (after adding record)
curl -I https://cdn.statlas.app/flags/us.svg
```

## ❓ Where is Your Main App Hosted?

**Tell me where your main application is hosted so I can give you the exact DNS record:**

- **Vercel** (for Next.js/React apps)
- **Netlify** (for static sites)
- **Google Cloud Run** (for containerized apps)
- **Firebase Hosting**
- **AWS CloudFront/S3**
- **Custom server/VPS**
- **Not hosted yet** (need recommendations)

## 🚀 Next Steps

1. **Add the main app DNS record** (depends on hosting platform)
2. **Add www redirect record**
3. **Add cdn record** for flag assets
4. **Wait 2-5 minutes** for DNS propagation
5. **Test all domains** work correctly

---

## 📞 Need Help?

If you're not sure about your hosting setup, let me know:
- Where do you plan to host the main Statlas web application?
- Do you have any existing hosting accounts (Vercel, Netlify, etc.)?

