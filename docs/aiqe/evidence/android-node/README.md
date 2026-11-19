# 真实 Android 设备能力验证（AUD-020）

- 设备：OnePlus ONEPLUS A6010，Android 11，1080x2340，serial `9f0564ba`
- App：`com.camelrn`，前台 Activity：`com.camelrn/.MainActivity`
- 工具：adb (platform-tools)（`adb shell monkey` 启动、`uiautomator dump`、`screencap`）
- AIQE 证据 Run：`0a631a4d-efc6-443b-bc70-4dd197c101a5`（`ANDROID-VERIFY-20261119T033706Z`）
- Artifacts：截图 `b2b7e37b-0c54-4a02-aed4-2dd0a8daac57`、UI XML `9716a0ed-d565-4af1-b4f7-eea1951a5f7e`、设备信息 `d8f31b10-3756-44b9-8660-fae7e8a72c75`
- Capability：node `android-oneplus6t-9f0564ba`，平台 `android`，状态 **VERIFIED**
- Preflight `native_android`：`READY`，blockers=[]

## 复现

```powershell
python scripts/aiqe/verify_android_device.py `
  --adb C:/Users/<user>/AppData/Local/Android/Sdk/platform-tools/adb.exe `
  --serial 9f0564ba --package com.camelrn
```

脚本会启动 App、抓取前台 Activity/UI/截图、写入 AIQE Artifact、注册并 VERIFIED 能力，最后输出
`native_android` Preflight 结果。

## 证据文件

- `screen-final.png`（SHA256 `8BEED98EF47415A92A9E6FF906388E492EDA58C718AAFF09CB062C48208CCAA3`）
- `window-final.xml`（SHA256 `B73BFB8DEC11E3A4D2733D5D009F32A72F10687C3941DE6A4B790C38D2F4E8BC`）
- `capability.json`

> 说明：设备为本地 USB 调试连接，仅验证 App 启动与首页渲染；未覆盖登录/下单等业务写操作。
