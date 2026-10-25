from dataclasses import replace
from importlib.resources import files
from math import isfinite
import pytest
from production_zero.data.definitions import load_card_definitions
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.core.mk_upgrades import mk_upgrade_cost, mk_factor, upgrade_payback_seconds

DEFS=load_card_definitions(files('production_zero.data')/'game_definitions.json')

@pytest.mark.parametrize('did',tuple(DEFS))
def test_all_98_mk_quotes_positive_monotone_for_every_family(did):
    d=DEFS[did];card=create_card_instance('test',did,d.card_kind,Rarity.COMMON)
    values=[mk_upgrade_cost(replace(card,mk_level=mk),d) for mk in range(1,99)]
    assert all(isfinite(x) and x>0 for x in values)
    assert all(a<b for a,b in zip(values,values[1:]))
    assert mk_factor(99)==25.5
    for rarity in Rarity:
        other=replace(card,rarity=rarity,output_bonus_percent=20)
        assert [mk_upgrade_cost(replace(other,mk_level=mk),d) for mk in (1,2,5,10,25,50,75,90,98)]==[values[mk-1] for mk in (1,2,5,10,25,50,75,90,98)]
    with pytest.raises(ValueError):mk_upgrade_cost(replace(card,mk_level=99),d)

@pytest.mark.parametrize('mk,seconds',((2,180),(10,600),(30,3600),(60,14400),(90,43200),(99,86400)))
def test_payback_design_anchors(mk,seconds):
    assert upgrade_payback_seconds(mk)==pytest.approx(seconds)
