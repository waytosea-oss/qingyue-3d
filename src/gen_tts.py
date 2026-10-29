# v7: pre-generate every line the web page speaks with Microsoft Edge TTS (edge-tts), plus a timeline of
# WordBoundary / SentenceBoundary events (seconds) used by the page to gate the lip-sync.
#   pip install edge-tts      then:   python3 src/gen_tts.py [--force]
import asyncio,json,os,sys,hashlib
import edge_tts
ROOT=os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','tts')
CFG=json.load(open(os.path.join(ROOT,'lines.json'),encoding='utf-8'))
FORCE='--force' in sys.argv
async def synth(line):
    key=hashlib.md5((CFG['voice']+CFG['rate']+CFG['pitch']+line['text']).encode()).hexdigest()[:8]
    mp3=os.path.join(ROOT,line['id']+'.mp3'); js=os.path.join(ROOT,line['id']+'.json')
    if not FORCE and os.path.exists(js) and json.load(open(js,encoding='utf-8')).get('key')==key and os.path.exists(mp3):
        return json.load(open(js,encoding='utf-8'))
    events=[]
    for boundary in ('WordBoundary','SentenceBoundary'):   # one pass per boundary type (edge-tts emits one kind per stream)
        c=edge_tts.Communicate(line['text'],CFG['voice'],rate=CFG['rate'],pitch=CFG['pitch'],boundary=boundary)
        audio=bytearray()
        async for ch in c.stream():
            if ch['type']=='audio': audio+=ch['data']
            elif ch['type'] in ('WordBoundary','SentenceBoundary'):
                events.append({'type':ch['type'],'t':round(ch['offset']/1e7,3),'d':round(ch['duration']/1e7,3),'text':ch['text']})
        if boundary=='WordBoundary': open(mp3,'wb').write(bytes(audio))
    words=[e for e in events if e['type']=='WordBoundary']
    meta={'id':line['id'],'group':line['group'],'text':line['text'],'file':line['id']+'.mp3','voice':CFG['voice'],'rate':CFG['rate'],'pitch':CFG['pitch'],
          'key':key,'duration':round(max([e['t']+e['d'] for e in events] or [0])+0.15,3),'words':words,'sentences':[e for e in events if e['type']=='SentenceBoundary']}
    json.dump(meta,open(js,'w',encoding='utf-8'),ensure_ascii=False,indent=1); return meta
async def main():
    man=[]
    for line in CFG['lines']:
        m=await synth(line); man.append({k:m[k] for k in ('id','group','text','file','duration')}|{'timeline':line['id']+'.json'})
        print('TTS',m['id'],'%.2fs'%m['duration'],len(m['words']),'words',len(m['sentences']),'sentences')
    json.dump({'voice':CFG['voice'],'rate':CFG['rate'],'pitch':CFG['pitch'],'lines':man},open(os.path.join(ROOT,'manifest.json'),'w',encoding='utf-8'),ensure_ascii=False,indent=1)
    print('TTS OK',len(man),'lines')
asyncio.run(main())
