---
name: doubao-tts
description: 豆包语音合成（火山引擎）接入与调用——HTTP 单向流式接口、鉴权、音色选型、语音指令、流解析模板。触发：需要 TTS 配音/旁白/语音播报时。
category: tools
created: 2026-09-29
---

# 豆包 TTS 通路

## 接口（已验证可用）

```
POST https://openspeech.bytedance.com/api/v3/tts/unidirectional
```

- HTTP Chunked 单向流式，一次输入文本，流式返回音频。适合预生成旁白/配音。
- 不用啃 WebSocket 二进制协议。

## 鉴权（.env 凭据，2026-09-20 接入）

```
X-Api-App-Key:    $DOUBAO_TTS_APP_ID
X-Api-Access-Key: $DOUBAO_TTS_ACCESS_TOKEN
X-Api-Resource-Id: seed-tts-2.0
X-Api-Request-Id:  唯一串
Content-Type: application/json
```

## 请求体

```json
{"req_params": {
  "text": "待合成文本",
  "speaker": "zh_male_shenyeboke_uranus_bigtts",
  "audio_params": {"format": "mp3", "sample_rate": 24000},
  "context_texts": ["用低沉、慵懒、平静的深夜电台旁白腔调说话，语速稍慢"]
}}
```

- `context_texts` 语音指令：自然语言控制情感/腔调，不参与计费，2.0 音色有效。
- 音色 ID 后缀规则：`_uranus_bigtts` / `saturn_` = 2.0（配 seed-tts-2.0）；`_moon_bigtts` / `_mars_bigtts` = 1.0（配 seed-tts-1.0）。用错资源报 55000000 resource mismatch。

## 响应解析（关键坑）

- chunked 流，**每个 chunk 是一个完整 JSON**：`{"code":0,"message":"","data":"<base64 mp3>"}`，多个 data 段顺序追加。
- `code:20000000 "OK"` = 合成结束（data 为 null）。
- 解析：逐 chunk 用 `json.JSONDecoder().raw_decode(s)` 循环取对象，`s = s[idx:].lstrip()` 消费。只解析首 chunk 会得到 0.3 秒残音频。

## 已踩坑

| 坑 | 现象 |
|---|---|
| `/api/v3/tts/create`（seed-audio-1.0） | 未开通，403 code=45000030 volc.service_type.10074 |
| `/tts/unidirectional/stream` | 假端点（GET only），正确 URL 无 `/stream` |
| vivi = `zh_female_vy_uranus_bigtts` | 不在 2.0 音色库，同系用 `vv_uranus` |
| 401 | 鉴权头组合错；403 | 认证过但资源未授权，看响应体 code |
| 测试样句升格为项目 | 对比带用的编造文案（爬月亮）被后续会话当真实项目引用、还起了片名——测试文案一律标注「测试」，不进项目叙事 |

## 官方文档

完整 API 参考 PDF 已归档 `data/documents/`（豆包语音_API参考，483 页，含错误码/声音复刻/ASR/同传）。
音色列表：volcengine.com/docs/DoubaoVoice/Tonelist-1（控制台音色库可看实际 ID）。

## 计费

- 语音合成 2.0：刊例 5 元/万字符（含标点；`context_texts` 语音指令不计费）
- **实际持有资源包（2026-09-29 购入）：16.8 元 / 10 万字符**（新客首单礼 6 折，折合 1.68 元/万），12 个月有效（至 2027-09）
- 经验值（按包内成本）：正片旁白 ~700 字 ≈ 0.12 元；选声对比带（8 段×70 字）≈ 0.2 元；10 万字符 ≈ 140 部短片旁白量
- 声音复刻音色年费约 150 元/年（高频固定音色才划算，按量更通用）

## 当前定稿参数（视频制作管线旁白备选，最终音色待拍板）

- 音色：`zh_male_shenyeboke_uranus_bigtts`（深夜播客）
- 指令：「用低沉、慵懒、平静的深夜电台旁白腔调说话，语速稍慢，带一点疲惫后的松弛感。」
- 备选：`zh_male_m191_uranus_bigtts`（云舟）+ 同指令
- 每镜单独 mp3 + enable_subtitle 字幕时间戳可开

## 可用工具脚本

测试脚本模板 `/tmp/tts_voices/test_v2.py`（临时目录，重写时按本文档请求/解析段重造）。
系统无 ffmpeg；拼接 MP3：剥 ID3v2 头（读前 10 字节 + syncsafe size）后二进制直连。
