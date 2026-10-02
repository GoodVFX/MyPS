#!/usr/bin/env python3
"""豆包 TTS 合成脚本（深夜播客·电台腔定稿参数）
用法: python3 synth.py "旁白文本" [输出路径]
依赖: .env 中 DOUBAO_TTS_APP_ID / DOUBAO_TTS_ACCESS_TOKEN
"""
import json, base64, urllib.request, os, sys

APP_ID = os.environ.get('DOUBAO_TTS_APP_ID', '')
TOKEN = os.environ.get('DOUBAO_TTS_ACCESS_TOKEN', '')
URL = 'https://openspeech.bytedance.com/api/v3/tts/unidirectional'

SPEAKER = 'zh_male_shenyeboke_uranus_bigtts'
INSTRUCTION = '用低沉、慵懒、平静的深夜电台旁白腔调说话，语速稍慢，带一点疲惫后的松弛感。'

def synth(text, speaker=SPEAKER, context=INSTRUCTION, timeout=120):
    p = {'text': text, 'speaker': speaker,
         'audio_params': {'format': 'mp3', 'sample_rate': 24000}}
    if context:
        p['context_texts'] = [context]
    req = urllib.request.Request(URL, data=json.dumps({'req_params': p}).encode(), headers={
        'Content-Type': 'application/json',
        'X-Api-App-Key': APP_ID, 'X-Api-Access-Key': TOKEN,
        'X-Api-Resource-Id': 'seed-tts-2.0',
        'X-Api-Request-Id': 'tts-' + str(abs(hash(text)))}, method='POST')
    audio, err = b'', ''
    with urllib.request.urlopen(req, timeout=timeout) as r:
        for chunk in r:
            s = chunk.decode(errors='replace').strip()
            while s:
                try:
                    obj, idx = json.JSONDecoder().raw_decode(s)
                except Exception:
                    break
                s = s[idx:].lstrip()
                if obj.get('data'):
                    audio += base64.b64decode(obj['data'])
                elif obj.get('code') not in (0, None, 20000000):
                    err = f"{obj.get('code')} {obj.get('message','')}"
    return audio, err

if __name__ == '__main__':
    text = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else '/tmp/tts_out.mp3'
    audio, err = synth(text)
    if audio:
        open(out, 'wb').write(audio)
        print(f'OK {len(audio)}B -> {out}')
    else:
        print(f'FAIL {err}')
        sys.exit(1)
