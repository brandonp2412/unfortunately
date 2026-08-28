#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv
from collections import Counter,defaultdict
from pathlib import Path
EXPECTED={2010:536,2011:438,2012:465,2013:523,2014:442,2015:358,2016:380,2017:341,2018:284,2019:271,2020:None,2021:None,2022:None,2023:None,2024:None,2025:None}

def write(path,rows,fields=None):
    path.parent.mkdir(parents=True,exist_ok=True)
    if fields is None: fields=list(rows[0]) if rows else []
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:r.get(k,'') for k in fields} for r in rows)

def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path('.'));a=p.parse_args();root=a.root.resolve()
    rows=[]
    for y in range(2010,2026):
        path=root/'output'/'uniform_scope'/f'{y}.csv'
        yr=list(csv.DictReader(path.open(newline='')))
        if EXPECTED[y] is not None and len(yr)!=EXPECTED[y]: raise SystemExit(f'{y} count {len(yr)}')
        rows.extend(yr)
    if len(rows)!=4898: raise SystemExit(f'expected 4898 all-search rows, got {len(rows)}')
    if len({r['pdf_url'] for r in rows})!=4898: raise SystemExit('duplicate PDF URL')
    write(root/'output'/'uniform_scope_2010_2025.csv',rows)
    audit=[r for r in rows if r.get('scope_audit_reason')]
    fields=['year','source_row_id','era_citation','case_name','prior_category','prior_outcome','scope_included','scope_reason','legal_dismissal_result','scope_audit_reason','scope_support','operative_excerpt','pdf_url']
    write(root/'output'/'uniform_scope_audit_queue.csv',audit,fields)
    included=[r for r in rows if r['scope_included']=='yes']
    c=Counter(r['legal_dismissal_result'] for r in included)
    by=defaultdict(lambda:Counter())
    for r in rows: by[r['year']]['included' if r['scope_included']=='yes' else 'excluded']+=1
    summary=[]
    for y in range(2010,2026): summary.append({'year':str(y),'search_rows':str(sum(by[str(y)].values())),'included':str(by[str(y)]['included']),'excluded':str(by[str(y)]['excluded'])})
    write(root/'output'/'uniform_scope_summary.csv',summary,['year','search_rows','included','excluded'])
    print(f'all_search=4898 included_provisional={len(included)} excluded_provisional={4898-len(included)} scope_audit_remaining={len(audit)}')
    print('provisional legal',dict(c))

if __name__=='__main__': main()
