import pyarrow.parquet as pq, pyarrow as pa, json
B="/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/data"
cs=pq.read_table(B+"/release22_cluster_split.parquet")
split_map=dict(zip(cs.column("cluster_id").to_pylist(), cs.column("split").to_pylist()))
pf=pq.ParquetFile(B+"/split_rebuild3/release22_cluster_8080.parquet")
out_path=B+"/release22_split_8080_recovered.parquet"
writer=None; n=0; kept=0
import collections
cnt=collections.Counter()
for b in pf.iter_batches(batch_size=200000,columns=["cluster_id","canonical_sequence","rna_type"]):
    cid=b.column("cluster_id").to_pylist(); seq=b.column("canonical_sequence").to_pylist(); rt=b.column("rna_type").to_pylist()
    sm=[]; s2=[]; r2=[]
    for c,s,r in zip(cid,seq,rt):
        sp=split_map.get(c)
        if sp is None: continue
        sm.append(sp); s2.append(s); r2.append(r); cnt[sp]+=1
    if not sm: continue
    t=pa.table({"split_membership":pa.array(sm,pa.string()),"canonical_sequence":pa.array(s2,pa.string()),"rna_type":pa.array(r2,pa.string())})
    if writer is None: writer=pq.ParquetWriter(out_path,t.schema,compression="zstd")
    writer.write_table(t); kept+=len(sm)
if writer: writer.close()
json.dump({"kept":kept,"counts":dict(cnt)},open("/teams/HoulabData_1788502323/liucunyu/rna-sc-p2/results/recovered_split_build.json","w"),indent=2)
print("kept",kept,"counts",dict(cnt))