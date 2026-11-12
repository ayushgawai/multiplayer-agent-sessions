import json, re, hashlib, statistics as st, collections as C
from pathlib import Path
import pandas as pd
R=Path(__file__).resolve().parents[2]
out={}
# ---- QMSum raw
raw={}
for sp in ('train','val','test'):
    docs=[json.loads(l) for l in open(R/f'data/qmsum/raw/{sp}.jsonl') if l.strip()]
    raw[sp]=docs
    out[f'qmsum_raw_{sp}']=dict(meetings=len(docs), keys=sorted(docs[0].keys()),
        specific=sum(len(d.get('specific_query_list',[])) for d in docs),
        general=sum(len(d.get('general_query_list',[])) for d in docs),
        turns=sum(len(d.get('meeting_transcripts',[])) for d in docs),
        topic=sum(len(d.get('topic_list',[])) for d in docs))
d0=raw['train'][0]
out['qmsum_raw_sample']={k:(json.dumps(v)[:300]) for k,v in d0.items()}
# meeting-level leakage: hash transcripts
def mh(d): return hashlib.sha256(json.dumps(d.get('meeting_transcripts'),sort_keys=True).encode()).hexdigest()
hs={sp:{mh(d) for d in raw[sp]} for sp in raw}
out['meeting_hash_overlap']={f'{a}&{b}':len(hs[a]&hs[b]) for a,b in (('train','val'),('train','test'),('val','test'))}
out['meeting_hash_unique']={sp:len(hs[sp]) for sp in hs}
# ---- splits
spl={}
for sp in ('train','val','test'):
    rows=[json.loads(l) for l in open(R/f'data/splits/m1_v1/{sp}.jsonl')]
    spl[sp]=rows
    w=lambda s: len(s.split())
    ref=[w(r['reference_summary']) for r in rows]; q=[w(r['query']) for r in rows]
    ns=[len(r['context_spans']) for r in rows]; cw=[sum(w(s) for s in r['context_spans']) for r in rows]
    kinds=C.Counter(re.search(r'_([sg])\d+$',r['id']).group(1) for r in rows)
    meetings={re.match(r'qmsum_\w+?_(\d+)_',r['id']).group(1) for r in rows}
    qs=lambda a:[round(x,1) for x in (min(a),st.quantiles(a,n=4)[0],st.median(a),st.quantiles(a,n=4)[2],st.quantiles(a,n=20)[18],max(a),st.mean(a))]
    out[f'split_{sp}']=dict(rows=len(rows),cols=sorted(rows[0].keys()),kinds=dict(kinds),meetings=len(meetings),
        ref_words_min_q1_med_q3_p95_max_mean=qs(ref),query_words=qs(q),n_spans=qs(ns),context_words=qs(cw),
        empty_query=sum(not r['query'].strip() for r in rows),empty_ref=sum(not r['reference_summary'].strip() for r in rows),empty_ctx=sum(not r['context_spans'] for r in rows),
        dup_ids=len(rows)-len({r['id'] for r in rows}))
ids={sp:{r['id'] for r in spl[sp]} for sp in spl}
out['id_overlap']={f'{a}&{b}':len(ids[a]&ids[b]) for a,b in (('train','val'),('train','test'),('val','test'))}
pair={sp:{(r['query'],r['reference_summary']) for r in spl[sp]} for sp in spl}
out['query_ref_pair_overlap']={f'{a}&{b}':len(pair[a]&pair[b]) for a,b in (('train','val'),('train','test'),('val','test'))}
refs={sp:{r['reference_summary'] for r in spl[sp]} for sp in spl}
out['ref_text_overlap']={f'{a}&{b}':len(refs[a]&refs[b]) for a,b in (('train','val'),('train','test'),('val','test'))}
ctx={sp:{hashlib.sha256('\n'.join(r['context_spans']).encode()).hexdigest() for r in spl[sp]} for sp in spl}
out['context_hash_overlap']={f'{a}&{b}':len(ctx[a]&ctx[b]) for a,b in (('train','val'),('train','test'),('val','test'))}
out['split_samples']={sp:{'id':spl[sp][1]['id'],'query':spl[sp][1]['query'],'n_spans':len(spl[sp][1]['context_spans']),'span0':spl[sp][1]['context_spans'][0][:260],'reference_summary':spl[sp][1]['reference_summary'][:330]} for sp in spl}
man=json.load(open(R/'data/splits/m1_v1/MANIFEST.json'))
out['manifest_sha_ok']={sp:hashlib.sha256(open(R/f'data/splits/m1_v1/{sp}.jsonl','rb').read()).hexdigest()==man['splits'][sp]['sha256'] for sp in spl}
# ---- MAST
m=json.load(open(R/'data/mast/hf/MAD_full_dataset.json'))
out['mast_raw']=dict(rows=len(m),top_keys=sorted(m[0].keys()),trace_keys=sorted(m[0]['trace'].keys()),ann_keys=sorted(m[0]['mast_annotation'].keys()))
x=m[400]
out['mast_raw_sample']={k:(v if not isinstance(v,(dict,list)) else None) for k,v in x.items()}
out['mast_raw_sample']['trace.key']=x['trace'].get('key'); out['mast_raw_sample']['trajectory_head']=x['trace']['trajectory'][:300]; out['mast_raw_sample']['mast_annotation']=x['mast_annotation']
out['mast_raw_null_sample']=[dict(mas=r['mas_name'],llm=r['llm_name'],bench=r['benchmark_name'],trace_id=r['trace_id'],key=r['trace'].get('key'),ann=r['mast_annotation']) for r in m if all(v is None for v in r['mast_annotation'].values())][:1]
ws=C.Counter(); 
for r in m:
    for f in ('mas_name','llm_name','benchmark_name'):
        v=r[f]
        if isinstance(v,str) and v!=v.strip(): ws[f]+=1
out['mast_whitespace_fixed']=dict(ws)
h=json.load(open(R/'data/mast/hf/MAD_human_labelled_dataset.json'))
out['mast_human']=dict(rows=len(h),keys=sorted(h[0].keys()) if isinstance(h,list) else list(h)[:5])
df=pd.read_csv(R/'data/mast/processed/mast_clean_summary.csv')
out['mast_clean']=dict(rows=len(df),cols=len(df.columns),columns=list(df.columns))
out['mast_clean_samples']=df[df.n_failures>0].sample(3,random_state=13).to_dict('records')+df.head(1).to_dict('records')
for f in ('mas_name','llm_name','benchmark_name'): out['mast_'+f]=df[f].value_counts().to_dict()
out['mast_trace_chars']=df.trace_chars.describe(percentiles=[.25,.5,.75,.95]).round(0).to_dict()
out['mast_nfail']=df.n_failures.describe().round(2).to_dict()
fc=[c for c in df.columns if c.startswith('fail_')]
out['mast_prev']={c:round(df[c].mean(),4) for c in fc}
out['mast_any_fail_by_fw']=(df.assign(a=df.n_failures>0).groupby('mas_name').a.mean().round(3)).to_dict()
out['mast_mean_nfail_by_fw']=df.groupby('mas_name').n_failures.mean().round(2).to_dict()
cor=df[fc].corr()
prs=sorted(((cor.loc[a,b],a,b) for i,a in enumerate(fc) for b in fc[i+1:]),reverse=True)
out['mast_top_corr']=[(round(v,3),a,b) for v,a,b in prs[:6]]; out['mast_low_corr']=[(round(v,3),a,b) for v,a,b in prs[-3:]]
out['mast_corr_len_nfail']=round(df[['trace_chars','n_failures']].corr(method='spearman').iloc[0,1],3)
em=json.load(open(R/'data/mast/eval_manifest.json'))
out['eval_manifest_keys']={k:(type(v).__name__, (len(v) if hasattr(v,'__len__') else v)) for k,v in em.items()}
json.dump(out,open(R/'docs/reports/t4a6_data_facts.json','w'),indent=1,default=str)
