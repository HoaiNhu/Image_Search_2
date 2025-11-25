# 🔧 FIX TIMEOUT - First Request Download Model

## ❌ Vấn Đề

```
timeout of 30000ms exceeded
Downloading MobileNetV2 model... (14MB)
```

**Nguyên nhân:**

- Lần đầu tiên request → MobileNetV2 phải download từ PyTorch (~14MB)
- Download mất 20-30 giây
- Frontend timeout sau 30 giây → FAIL!

---

## ✅ Giải Pháp (2 Fix)

### 1. **Pre-download Model trong Docker Build** 🎯 (BEST!)

**Thay đổi:** Model được download TRONG quá trình build Docker, không phải khi runtime!

**Lợi ích:**

- ✅ First request chỉ mất 1-2 giây (không download)
- ✅ Không cần tăng timeout
- ✅ User experience tốt ngay từ đầu

**Đã thêm vào Dockerfile:**

```dockerfile
# Pre-download MobileNetV2 model during build
RUN python -c "import torch; import torchvision; torchvision.models.mobilenet_v2(weights='IMAGENET1K_V1')" \
    && echo "MobileNetV2 model pre-downloaded successfully!"
```

### 2. **Tăng Timeout Frontend** (Backup)

**Thay đổi:** 30s → 60s

**File:** `FE-Project_AvocadoCake/src/app/api/services/ImageSearchService.js`

```javascript
timeout: 60000, // 60 second timeout (was 30000)
```

---

## 🚀 Deploy

### SEARCH_IMG_2 (Backend):

```bash
cd C:\Users\Lenovo\STUDY\SEARCH_IMG_2
git add -A
git commit -m "fix: pre-download MobileNetV2 in Docker, fix timeout"
git push origin main
```

**Trên Render:**

- Click **Manual Deploy**
- Đợi build (sẽ mất ~2-3 phút build lần đầu)
- Model sẽ được download trong build time!

### FE-Project_AvocadoCake (Frontend):

```bash
cd C:\Users\Lenovo\STUDY\FE-Project_AvocadoCake
git add src/app/api/services/ImageSearchService.js
git commit -m "fix: increase image search timeout to 60s"
git push origin main
```

---

## 📊 Timeline

### Trước Fix:

```
User upload image
    ↓
Frontend request (timeout 30s)
    ↓
Backend starts
    ↓
Download MobileNetV2... (20-30s) ❌ TIMEOUT!
```

### Sau Fix (Solution 1 - Pre-download):

```
Docker build (one-time):
    ↓
Download MobileNetV2 (30s)
    ↓
Build complete

Runtime:
User upload image
    ↓
Frontend request (timeout 60s)
    ↓
Backend starts
    ↓
Load model from disk (< 1s) ✅
    ↓
Search (1-2s) ✅
    ↓
Return results ✅
```

---

## ⏱️ Expected Performance

### First Deployment (Build Time):

- Build time: **3-4 minutes** (thêm 30s để download model)
- One-time cost!

### Runtime (After Deploy):

- **First request**: 1-2 giây ✅
- **Subsequent**: 0.3-0.5 giây ✅
- **No timeout!** ✅

---

## 🧪 Test Sau Deploy

### 1. Check Logs

Sau khi deploy, check Render logs:

```
✅ "MobileNetV2 model pre-downloaded successfully!"
✅ "Loading MobileNetV2 model (14MB, very lightweight!)"
✅ "MobileNetV2 loaded successfully"
```

### 2. Test First Request

```bash
curl -X POST https://your-app.onrender.com/api/v1/search/url \
  -H "Content-Type: application/json" \
  -d '{"image_url": "https://picsum.photos/400", "top_k": 5}'
```

**Should return in 1-2 seconds!** ✅

### 3. Test từ Frontend

- Upload ảnh từ UI
- **Không timeout nữa!**
- Kết quả về trong 1-2 giây

---

## 🔍 Troubleshooting

### Vẫn Timeout?

**Check 1: Model có được download trong build không?**

Xem Render build logs:

```
✅ "MobileNetV2 model pre-downloaded successfully!"
```

Nếu không thấy → Build lại

**Check 2: Timeout setting của frontend**

File: `ImageSearchService.js`

```javascript
timeout: 60000, // Should be 60000, not 30000
```

**Check 3: Render service có đang sleep không?**

Render free tier sleep sau 15 phút không hoạt động.
First request sau khi wake up có thể mất 10-20s để cold start.

---

## 💡 Giải Thích Kỹ Thuật

### PyTorch Model Loading:

1. **First time (no cache):**

   - Download from `download.pytorch.org`
   - Save to `/root/.cache/torch/hub/checkpoints/`
   - Load into memory

2. **Subsequent times (cached):**
   - Load from cache (very fast)
   - No download needed

### Docker Build vs Runtime:

**Without pre-download:**

- Build: Quick (2 min)
- Runtime first request: Slow (30s download) ❌

**With pre-download:**

- Build: Slower (3 min, includes download)
- Runtime first request: Fast (1s load) ✅

---

## 📦 Docker Image Size

### Before:

- Base image: ~1GB
- Dependencies: ~800MB
- **Total**: ~1.8GB

### After (with pre-downloaded model):

- Base image: ~1GB
- Dependencies: ~800MB
- MobileNetV2 cached: 14MB
- **Total**: ~1.81GB

**Trade-off:** +14MB image size for instant startup! Worth it! ✅

---

## ✅ Summary

**Changes:**

1. ✅ Pre-download MobileNetV2 in Dockerfile
2. ✅ Fix deprecated `pretrained=True` → `weights='IMAGENET1K_V1'`
3. ✅ Increase frontend timeout 30s → 60s (backup)

**Benefits:**

- ✅ No download during runtime
- ✅ First request: 1-2s (not 30s!)
- ✅ No timeout errors
- ✅ Better user experience

**Deploy và test ngay!** 🚀

---

## 📝 Files Changed

### Backend (SEARCH_IMG_2):

- `Dockerfile` - Pre-download model
- `src/services/feature_extractor.py` - Fix deprecated warning

### Frontend (FE-Project_AvocadoCake):

- `src/app/api/services/ImageSearchService.js` - Increase timeout

**All done!** ✨
