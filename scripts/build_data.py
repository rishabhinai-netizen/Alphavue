#!/usr/bin/env python3
"""
AlphaVue — Data Pipeline
Run weekly to refresh alphavue.html with latest Nifty 500 scores.

Usage:
    python build_data.py

Requires: yfinance pandas numpy requests
    pip install yfinance pandas numpy requests
"""

import yfinance as yf
import pandas as pd
import numpy as np
import requests, io, json, re, warnings
from datetime import datetime, timedelta
warnings.filterwarnings('ignore')

print("AlphaVue Data Pipeline")
print("=" * 40)

# 1. Fetch Nifty 500 list
print("Fetching Nifty 500 list...")
url = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"
headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
r = requests.get(url, headers=headers, timeout=15)
df_stocks = pd.read_csv(io.StringIO(r.text))
symbols = df_stocks['Symbol'].tolist()
sym_map = dict(zip(df_stocks['Symbol'], df_stocks['Company Name']))
ind_map = dict(zip(df_stocks['Symbol'], df_stocks['Industry']))
print(f"  {len(symbols)} stocks loaded")

# 2. Fetch 1 year of price/volume data
print("Fetching price data (this takes ~2 minutes)...")
yf_symbols = [s + ".NS" for s in symbols]
end = datetime.today()
start = end - timedelta(days=400)
data = yf.download(yf_symbols, start=start.strftime('%Y-%m-%d'), 
                   end=end.strftime('%Y-%m-%d'), auto_adjust=True, 
                   progress=False, threads=True)
close = data['Close']
volume = data['Volume']
print(f"  Data: {close.index[0].date()} → {close.index[-1].date()}, {close.iloc[-1].notna().sum()} stocks")

# 3. Compute all metrics
print("Computing metrics for all stocks...")

def safe_roc(s, n):
    if len(s) < n+1: return np.nan
    return (s.iloc[-1] / s.iloc[-n-1] - 1) * 100

results = []
for sym_ns in close.columns:
    sym = sym_ns.replace('.NS','')
    s = close[sym_ns].dropna()
    v = volume[sym_ns].dropna()
    if len(s) < 30: continue
    
    r1d = safe_roc(s,1); r5d = safe_roc(s,5); r1m = safe_roc(s,21)
    r3m = safe_roc(s,63); r6m = safe_roc(s,126); r1y = safe_roc(s,252)
    
    ma10=s.rolling(10).mean().iloc[-1]; ma20=s.rolling(20).mean().iloc[-1]
    ma50=s.rolling(50).mean().iloc[-1]; ma200=s.rolling(200).mean().iloc[-1] if len(s)>=200 else np.nan
    price = s.iloc[-1]
    
    high52=s.tail(252).max() if len(s)>=252 else s.max()
    low52=s.tail(252).min() if len(s)>=252 else s.min()
    pct52h=(price/high52-1)*100; pct52l=(price/low52-1)*100
    
    daily_rets=s.pct_change().dropna()
    consistency=(daily_rets.tail(20)>0).mean()*100
    vol20=daily_rets.tail(20).std()*np.sqrt(252)*100
    
    s3m=s.tail(63); rm=s3m.expanding().max(); dd3m=((s3m/rm-1).min())*100
    s1y=s.tail(252) if len(s)>=252 else s; rm1y=s1y.expanding().max(); dd1y=((s1y/rm1y-1).min())*100
    calmar=(r3m/abs(dd3m)) if dd3m!=0 and not np.isnan(r3m) else np.nan
    
    avg_vol20=v.tail(20).mean(); avg_val_cr=(avg_vol20*price)/1e7
    avg_vol5=v.tail(5).mean(); vol_ratio=avg_vol5/avg_vol20 if avg_vol20>0 else np.nan
    
    hl=s.tail(10).values
    hl_trend=1 if (hl[-1]>hl[-3]>hl[-6]) else 0
    price_5d_chg=r5d if not np.isnan(r5d) else 0
    vpa=1 if (price_5d_chg>0 and (vol_ratio or 0)>1) else 0
    
    results.append({
        'symbol':sym,'company':sym_map.get(sym,sym),'industry':ind_map.get(sym,''),
        'price':round(price,2),
        'ret_1d':round(r1d,2) if not np.isnan(r1d) else None,
        'ret_5d':round(r5d,2) if not np.isnan(r5d) else None,
        'ret_1m':round(r1m,2) if not np.isnan(r1m) else None,
        'ret_3m':round(r3m,2) if not np.isnan(r3m) else None,
        'ret_6m':round(r6m,2) if not np.isnan(r6m) else None,
        'ret_1y':round(r1y,2) if not np.isnan(r1y) else None,
        'above_ma20':int(price>ma20),'above_ma50':int(price>ma50),
        'above_ma200':int(price>ma200) if not np.isnan(ma200) else 0,
        'ma20_above_ma50':int(ma20>ma50),
        'pct_from_52w_high':round(pct52h,1),'pct_from_52w_low':round(pct52l,1),
        'consistency_20d':round(consistency,1),'hl_trend':hl_trend,'vol_price_alignment':vpa,
        'vol_20d':round(vol20,1),'max_dd_3m':round(dd3m,1),'max_dd_1y':round(dd1y,1),
        'calmar_3m':round(calmar,2) if not np.isnan(calmar) else None,
        'avg_vol_20d':int(avg_vol20),'avg_daily_val_cr':round(avg_val_cr,1),
        'vol_ratio_5d_20d':round(vol_ratio,2) if not np.isnan(vol_ratio) else None,
    })

df = pd.DataFrame(results)

# RS ranks
df['rs_rank_1m']=df['ret_1m'].rank(pct=True)*100
df['rs_rank_3m']=df['ret_3m'].rank(pct=True)*100
df['rs_rank_6m']=df['ret_6m'].rank(pct=True)*100
df['rs_rank_1y']=df['ret_1y'].rank(pct=True)*100
df['rs_composite']=(df['rs_rank_1m']*0.4+df['rs_rank_3m']*0.3+df['rs_rank_6m']*0.2+df['rs_rank_1y']*0.1).round(1)

# Scores
liq=(df['avg_vol_20d']>=100000)&(df['avg_daily_val_cr']>=2)
df['mom_score']=(df['rs_rank_1m'].fillna(50)*0.45+df['rs_rank_3m'].fillna(50)*0.30+df['rs_rank_6m'].fillna(50)*0.15+df['rs_rank_1y'].fillna(50)*0.10).round(1)
trend_pts=(df['above_ma20'].fillna(0)*25+df['above_ma50'].fillna(0)*25+df['above_ma200'].fillna(0)*25+df['ma20_above_ma50'].fillna(0)*25)
def h52b(p): return 15 if p>=-5 else 5 if p>=-15 else 0
df['trend_score']=(trend_pts+df['pct_from_52w_high'].apply(h52b)).clip(0,100)
def vs(row):
    s=50; vr=row['vol_ratio_5d_20d']
    if pd.isna(vr): return 50
    if vr>=2: s+=30
    elif vr>=1.5: s+=20
    elif vr>=1.2: s+=10
    elif vr<0.7: s-=20
    if row['vol_price_alignment']==1: s+=15
    elif row['vol_price_alignment']==-1: s-=10
    return max(0,min(100,s))
df['volume_score']=df.apply(vs,axis=1)
df['consistency_score']=(df['consistency_20d'].fillna(50)+df['hl_trend'].fillna(0)*20).clip(0,100)
def rs(row):
    s=50; cal=row['calmar_3m']
    if not pd.isna(cal):
        if cal>=2: s+=30
        elif cal>=1: s+=15
        elif cal>=0: s+=5
        else: s-=20
    if row['max_dd_3m']<-20: s-=20
    elif row['max_dd_3m']<-10: s-=10
    return max(0,min(100,s))
df['risk_score']=df.apply(rs,axis=1)
df['composite_score']=(df['mom_score']*0.35+df['trend_score']*0.25+df['volume_score']*0.15+df['consistency_score']*0.15+df['risk_score']*0.10).round(1)
df.loc[~liq,'composite_score']=np.nan
def grade(s):
    if pd.isna(s): return 'NQ'
    if s>=80: return 'S'
    if s>=70: return 'A'
    if s>=55: return 'B'
    if s>=40: return 'C'
    return 'D'
df['grade']=df['composite_score'].apply(grade)

print(f"  Scored {len(df)} stocks · S:{(df['grade']=='S').sum()} A:{(df['grade']=='A').sum()} B:{(df['grade']=='B').sum()}")

# 4. Build full_scores JSON
def gv(v): return None if pd.isna(v) else round(float(v),2)
full_scores = sorted([{
    'sym':r.symbol,'co':str(r.company)[:28],'ind':str(r.industry),
    'grade':str(r.grade),'score':gv(r.composite_score) or 0,
    'r1d':gv(r.ret_1d),'r5d':gv(r.ret_5d),'r1m':gv(r.ret_1m),
    'r3m':gv(r.ret_3m),'r6m':gv(r.ret_6m),'r1y':gv(r.ret_1y),
    'dd3m':gv(r.max_dd_3m),'val':gv(r.avg_daily_val_cr) or 0,
    'pct52h':gv(r.pct_from_52w_high),'vr':gv(r.vol_ratio_5d_20d),
    'mom':gv(r.mom_score) or 0,'trend':gv(r.trend_score) or 0,
    'volsc':gv(r.volume_score) or 0,'cons':gv(r.consistency_20d) or 50,
    'above200':int(gv(r.above_ma200) or 0),'vpa':int(gv(r.vol_price_alignment) or 0),
    'rs1m':gv(r.rs_rank_1m) or 0,'pct52l':gv(r.pct_from_52w_low),'price':gv(r.price),
} for _,r in df.iterrows() if not pd.isna(r.composite_score)], key=lambda x:-(x['score'] or 0))

# 5. 15-day performance
print("Computing 15-day returns...")
close_15=close.tail(15)
dates_15=[str(d.date()) for d in close_15.index]

def pcurve(syms):
    cs=[(close_15[s+'.NS'].dropna()/close_15[s+'.NS'].dropna().iloc[0]*100).values for s in syms if s+'.NS' in close_15.columns and len(close_15[s+'.NS'].dropna())>=2]
    return np.mean(cs,axis=0).round(2).tolist() if cs else [100]*15

s_syms=df[df['grade']=='S']['symbol'].tolist()
sa_syms=df[df['grade'].isin(['S','A'])]['symbol'].tolist()
s_curve=pcurve(s_syms); sa_curve=pcurve(sa_syms)
all_c=[(close_15[c].dropna()/close_15[c].dropna().iloc[0]*100).values for c in close_15.columns if len(close_15[c].dropna())==15]
n500_curve=np.mean(all_c,axis=0).round(2).tolist()

stocks15=[]
sc_idx=df.set_index('symbol')
for sym in sa_syms:
    s15=close_15.get(sym+'.NS',pd.Series()).dropna()
    if len(s15)<2: continue
    pl=[round(p,2) for p in s15.values]
    dr=[round((pl[i]/pl[i-1]-1)*100,2) for i in range(1,len(pl))]
    sc=sc_idx.loc[sym] if sym in sc_idx.index else None
    def sv(col): return None if sc is None or pd.isna(sc[col]) else round(float(sc[col]),2)
    ret15=round((pl[-1]/pl[0]-1)*100,2)
    stocks15.append({'sym':sym,'co':str(sc['company'])[:28] if sc is not None else sym,'ind':str(sc['industry']) if sc is not None else '','grade':sc['grade'] if sc is not None else 'A','score':sv('composite_score') or 0,'ret15':ret15,'daily_rets':dr,'prices':pl,'entry':pl[0],'exit':pl[-1],'mom':sv('mom_score') or 0,'trend':sv('trend_score') or 0,'volsc':sv('volume_score') or 0,'r1m':sv('ret_1m'),'r3m':sv('ret_3m'),'r6m':sv('ret_6m'),'r1y':sv('ret_1y'),'dd3m':sv('max_dd_3m'),'val':sv('avg_daily_val_cr') or 0,'pct52h':sv('pct_from_52w_high'),'vr':sv('vol_ratio_5d_20d'),'above200':int(sv('above_ma200') or 0),})
stocks15.sort(key=lambda x:x['ret15'],reverse=True)

invest=100000
s_data=[r for r in stocks15 if r['grade']=='S']
sa_data=stocks15
s_gain=sum(invest/len(s_data)*r['ret15']/100 for r in s_data) if s_data else 0
sa_gain=sum(invest/len(sa_data)*r['ret15']/100 for r in sa_data) if sa_data else 0
n500_ret=round(n500_curve[-1]-100,2)

sp={}
for r in stocks15: sp.setdefault(r['ind'],[]).append(r['ret15'])
sector_avg=sorted([(k,round(np.mean(v),2)) for k,v in sp.items() if len(v)>=2],key=lambda x:-x[1])

summary={'s_ret':round(s_curve[-1]-100,2),'sa_ret':round(sa_curve[-1]-100,2),'n500_ret':n500_ret,'s_gain':round(s_gain,0),'sa_gain':round(sa_gain,0),'n500_gain':round(invest*n500_ret/100,0),'n_s':len(s_data),'n_sa':len(sa_data),'best_sym':stocks15[0]['sym'] if stocks15 else '','best_ret':stocks15[0]['ret15'] if stocks15 else 0,'alpha_s':round(s_curve[-1]-100-n500_ret,2)}

# 6. Inject into HTML
as_of=close.index[-1].strftime('%Y-%m-%d')
js_data=f"""const AV_DATA = {{
  dates: {json.dumps(dates_15)},
  s_curve: {json.dumps(s_curve)},
  sa_curve: {json.dumps(sa_curve)},
  n500_curve: {json.dumps(n500_curve)},
  summary: {json.dumps(summary)},
  sector_avg: {json.dumps(sector_avg[:12])},
  stocks15: {json.dumps(stocks15)},
  scores: {json.dumps(full_scores)},
  as_of: "{as_of}"
}};"""

with open('alphavue.html','r') as f: html=f.read()
html=re.sub(r'const AV_DATA = \{.*?\};', js_data, html, flags=re.DOTALL)
with open('alphavue.html','w') as f: f.write(html)

print(f"\nDone! alphavue.html updated: {len(html.encode())//1024}KB")
print(f"S-grade 15d: +{summary['s_ret']}% | Alpha: +{summary['alpha_s']}% vs N500")
print(f"Run complete. Open alphavue.html in browser.")
