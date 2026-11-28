import pyarrow.parquet as pq, collections, json
B="/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/data"
cs=pq.read_table(B+"/release22_cluster_split.parquet")
split_map=dict(zip(cs.column("cluster_id").to_pylist(), cs.column("split").to_pylist()))
pf=pq.ParquetFile(B+"/split_rebuild3/release22_cluster_8080.parquet")
cnt=collections.Counter(); miss=0; n=0
for b in pf.iter_batches(batch_size=200000,columns=["cluster_id"]):
    for cid in b.column("cluster_id").to_pylist():
        n+=1; s=split_map.get(cid)
        if s is None: miss+=1
        else: cnt[s]+=1
target={"train":14130321,"validation":164280,"test":108979,"family_validation":7525752,"family_test":7082895}
out={"total":n,"unmatched":miss,"counts":dict(cnt),"diff":{k:cnt.get(k,0)-v for k,v in target.items()}}
json.dump(out,open("/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/results/split_join_verify.json","w"),indent=2)
print(json.dumps(out))