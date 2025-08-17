# 🌐 Cloudflare CDN Setup for Flag Assets

This guide walks you through setting up Cloudflare CDN for the Statlas flag assets.

## 📋 Prerequisites

- ✅ Domain `statlas.app` registered and using Cloudflare DNS
- ✅ Flag assets uploaded to `gs://statlas-flag-assets/flags/`
- ✅ Access to Cloudflare dashboard

## 🚀 Setup Steps

### Step 1: Add DNS Record

**In your Cloudflare dashboard:**

1. Go to **statlas.app** → **DNS** → **Records**
2. Click **Add record**
3. Configure:
   ```
   Type: CNAME
   Name: cdn
   Target: statlas-flag-assets.storage.googleapis.com
   Proxy status: Proxied (🟠 orange cloud) ← IMPORTANT!
   TTL: Auto
   ```
4. Click **Save**

### Step 2: Configure SSL/TLS Settings

**In Cloudflare dashboard → statlas.app → SSL/TLS:**

1. **Overview tab:**
   - SSL/TLS encryption mode: **Full (strict)**

2. **Edge Certificates tab:**
   - Always Use HTTPS: **On**
   - Minimum TLS Version: **1.2**
   - Automatic HTTPS Rewrites: **On**

### Step 3: Add Page Rules (Optional but Recommended)

**In Cloudflare dashboard → statlas.app → Rules → Page Rules:**

1. Click **Create Page Rule**
2. Configure:
   ```
   URL: cdn.statlas.app/flags/*
   
   Settings:
   - Cache Level: Cache Everything
   - Browser Cache TTL: 1 year
   - Edge Cache TTL: 1 month
   ```
3. Click **Save and Deploy**

### Step 4: Verify DNS Propagation

Wait 2-5 minutes, then test:

```bash
# Check DNS resolution
dig cdn.statlas.app

# Should show Cloudflare IPs (e.g., 104.21.x.x or 172.67.x.x)
```

### Step 5: Test CDN Functionality

```bash
# Test flag access
curl -I https://cdn.statlas.app/flags/us.svg

# Should return:
# HTTP/2 200
# cf-cache-status: HIT (after first request)
# content-type: image/svg+xml
```

### Step 6: Update Country Flag URLs

```bash
# Test the update (dry run)
cd scripts
python update_country_flag_urls.py --dry-run

# If everything looks good, run the actual update
python update_country_flag_urls.py
```

## 🧪 Verification Checklist

- [ ] DNS record added and proxied through Cloudflare
- [ ] SSL/TLS configured for Full (strict) mode
- [ ] Page rules configured for optimal caching
- [ ] `https://cdn.statlas.app/flags/us.svg` returns the US flag
- [ ] Response headers show `cf-cache-status: HIT` on subsequent requests
- [ ] All country flag URLs updated in Firestore

## 📊 Expected Performance

**After setup:**
- **Global CDN**: 195+ edge locations worldwide
- **Cache TTL**: 1 month at edge, 1 year in browser
- **SSL**: Automatic with Cloudflare certificates
- **Bandwidth**: Unlimited and free
- **Latency**: <50ms globally for cached assets

## 🔧 Troubleshooting

### DNS Not Resolving
- Wait up to 24 hours for full propagation
- Ensure orange cloud (proxy) is enabled
- Check Cloudflare status page

### 404 Errors
- Verify Google Cloud Storage bucket is public
- Check bucket name spelling: `statlas-flag-assets`
- Ensure files exist in `/flags/` folder

### SSL Errors
- Ensure SSL mode is "Full (strict)"
- Wait for SSL certificate provisioning (up to 24 hours)
- Check certificate status in SSL/TLS → Edge Certificates

### Cache Issues
- Use Cloudflare dashboard to purge cache
- Check page rules are configured correctly
- Verify `Cache-Control` headers from origin

## 🎯 Next Steps

After successful setup:

1. **Monitor performance** in Cloudflare Analytics
2. **Set up alerts** for downtime or errors
3. **Consider Workers** for advanced features (image resizing, WebP conversion)
4. **Add more subdomains** as needed (api.statlas.app, etc.)

## 📞 Support

If you encounter issues:
- Check Cloudflare Community: https://community.cloudflare.com/
- Cloudflare Support: https://support.cloudflare.com/
- Google Cloud Storage docs: https://cloud.google.com/storage/docs

