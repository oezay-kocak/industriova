"""Bounded aggregate stress, 1M completions; isolated diagnostic, not gameplay."""
import os,sys,json,time,tracemalloc,statistics
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'artifacts/phase6';sys.path.insert(0,str(ROOT/'src'))
from production_zero.core.freight_statistics import FreightDeliveryStatistics
stats=FreightDeliveryStatistics();rows=[];tracemalloc.start();batch_start=time.perf_counter()
# 500 vehicles, 20 facilities, a batch of completions every 60 seconds.
# Beyond ten minutes neither bucket count nor owner counts grow with elapsed time.
for index in range(1_000_000):
    if index%500==0:stats.advance(60)
    cid=index%500;stats.record(f'card-{cid}',f'facility-{cid//25}',sell=3,contract=2,consortium=1)
    if index+1 in (1000,100000,500000,1000000):
        current,peak=tracemalloc.get_traced_memory();t=time.perf_counter()
        payload=stats.snapshot();snapshot_ms=(time.perf_counter()-t)*1000
        row=dict(completions=index+1,simulation_seconds=stats.seconds,occupied_buckets=len(stats.buckets),aggregated_owner_pairs=sum(len(b) for b in stats.buckets.values()),
                 vehicle_indexes=len(stats._vehicles),facility_indexes=len(stats._facilities),python_current_bytes=current,python_peak_bytes=peak,
                 snapshot_bytes=len(json.dumps(payload).encode()),snapshot_ms=snapshot_ms,elapsed_wall_seconds=time.perf_counter()-batch_start)
        assert row['occupied_buckets']<=10 and row['aggregated_owner_pairs']<=5000
        assert stats.rate(facility_id='facility-0').total==150
        rows.append(row);print(json.dumps(row),flush=True)
tracemalloc.stop()
samples=[]
for _ in range(7):
    t=time.perf_counter()
    for i in range(1000):stats.record(f'card-{i%500}',f'facility-{i%500//25}',sell=1)
    samples.append((time.perf_counter()-t)*1000)
stats.advance(600)
assert not stats.buckets and not stats._vehicles and not stats._facilities
(OUT/'stress.json').write_text(json.dumps(dict(method='Synthetic allocation-only stress, 500 identities in 20 facilities; actual completion boundary is separately covered by engine tests and completion-tick benchmarks. tracemalloc enabled: wall times instrumented, not compared to normal benchmarks. 60 simulation seconds every batch of 500 records. No shipment-ID history.',checkpoints=rows,untraced_1000_record_samples_ms=samples,expired_empty=True),indent=2),encoding='utf8')
