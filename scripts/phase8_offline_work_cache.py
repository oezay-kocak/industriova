"""Offline engine runs only: reuse pure immutable catalog work after equality proof.

Never imported by production or the performance benchmark. Simulation ticks,
input debits, fuel, storage, freight, XP rules and clock remain the real engine.
"""
import hashlib,json
_installed=False
_proof=None
def install(definitions):
    global _installed,_proof
    if _installed:return _proof
    import production_zero.core.company_xp as xp
    original=xp.ProductionValueCalculator
    calculator=original(definitions)
    reference=original(definitions)
    proof=[]
    for rid,value in sorted(reference.values().items()):
        actual=calculator.value_for_resource(rid)
        assert actual==value,(rid,actual,value)
        proof.append((rid,str(value.value_per_unit)))
    cache={tuple((key,id(value)) for key,value in definitions.items()):calculator}
    def cached(current):
        signature=tuple((key,id(value)) for key,value in current.items())
        if signature not in cache:cache[signature]=original(current)
        return cache[signature]
    xp.ProductionValueCalculator=cached
    _installed=True
    _proof=dict(resources=len(proof),value_sha256=hashlib.sha256(json.dumps(proof).encode()).hexdigest(),scope='Only the offline harness reuses pure catalog work in company_xp; no game state cached and no SimulationEngine transition altered. Benchmarks do not install this helper.')
    return _proof
