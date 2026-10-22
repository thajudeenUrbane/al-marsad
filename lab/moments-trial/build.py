import json,hashlib,sys,re,collections
sys.path.insert(0,sys.argv[1]); from moments_src import M
root=sys.argv[2]; out=root+"/lab/moments-trial"
t=open(out+"/cache/source.txt",encoding="utf-8").read()
P={}
for l in open(root+"/ingest/claims/ibn-hisham-full-passages.jsonl"):
    d=json.loads(l); P[d["key"]]=d
seqs=collections.Counter(); pub=[]; priv=[]; bad=0
for i,(sec,actors,action,place,tc,quote,kind,hedge,chain) in enumerate(M,1):
    p=P[sec]; s=t[p["start"]:p["end"]]
    n=s.count(quote)
    if n==0: print("MISSING",sec,quote); bad+=1; continue
    r=s.find(quote); a=p["start"]+r; b=a+len(quote)
    assert t[a:b]==quote
    seqs[sec]+=1
    rec={"id":f"mom-{i:03d}","section":sec,"passage":p["id"],"seq":seqs[sec],"global_seq":i,"actors":actors,"action":action,
         "place":place,"time_cue":tc,"kind":kind,"hedge":hedge,"narrator_chain_note":chain,
         "span":[r,r+len(quote)],"source_offsets":[a,b],"span_sha256":hashlib.sha256(quote.encode()).hexdigest(),
         "quote_occurrences_in_section":n,"status":"proposed"}
    rec={k:v for k,v in rec.items() if v is not None}
    pub.append(rec); priv.append(dict(rec,quote=quote))
    if n>1: print("NONUNIQUE",sec,n,quote)
arab=re.compile(r"[؀-ۿ]")
with open(out+"/moments.jsonl","w",encoding="utf-8") as f:
    for r in pub:
        line=json.dumps(r,ensure_ascii=False); assert not arab.search(line),line; f.write(line+"\n")
with open(out+"/cache/moments-with-quotes.jsonl","w",encoding="utf-8") as f:
    for r in priv: f.write(json.dumps(r,ensure_ascii=False)+"\n")
print("ok",len(pub),"bad",bad,dict(collections.Counter(r["kind"] for r in pub)),"sections",len(seqs),"hedged",sum(1 for r in pub if "hedge" in r))
print(sorted(seqs.items()))
