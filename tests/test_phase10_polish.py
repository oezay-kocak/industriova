"""P10 display, genesis and atomic confirmation boundaries."""
from copy import deepcopy
from decimal import Decimal
from importlib.resources import files
import pytest
from production_zero.data.definitions import load_card_definitions, load_resource_definitions
from production_zero.ui.main_window import _create_initial_state
from production_zero.ui.resource_prices import price_number
from production_zero.persistence.sqlite_store import serialize_game_state, deserialize_game_state, STATE_SCHEMA_VERSION
from production_zero.core.commands import (RenameHall, ExpandInventoryStorage, BuyCommonSupplyCard,
    InstallInventoryCards, InstallCardInHall, ReturnMachinesToInventory, SellMachines)
from production_zero.core.infrastructure_prices import production_facility_price
from production_zero.core.storage_upgrades import inventory_storage_upgrade_cost
from production_zero.core.machine_operations import resale_value


@pytest.fixture
def definitions():
    return load_card_definitions(files('production_zero.data') / 'game_definitions.json')


@pytest.fixture
def resources():
    return load_resource_definitions(files('production_zero.data') / 'resource_definitions.json')


@pytest.mark.parametrize('value,expected',[(497.4,'497.40'),(10,'10.00'),(1.1,'1.10'),
    (226.1625,'226.17'),(1.8125,'1.82'),(.000001,'0.01'),(0,'0.00'),
    (Decimal('1.01000000000000000001'),'1.02'),(1e30,'1,000,000,000,000,000,000,000,000,000,000.00')])
def test_cent_display_ceiling_without_altering_value(value,expected):
    original = value
    assert price_number(value) == expected and value == original


@pytest.mark.parametrize('value',[float('nan'),float('inf'),float('-inf')])
def test_nonfinite_price_rejected(value):
    with pytest.raises(ValueError): price_number(value)


@pytest.mark.parametrize('value,expected',[(1.1*1.1,'1.21'),(.1+.2,'0.30'),
    (1.01000000000001,'1.02'),(Decimal('1.21000000000000000001'),'1.22')])
def test_only_binary_cent_noise_is_removed(value,expected):
    assert price_number(value)==expected


def test_genesis_three_free_sites_no_extra_cards_or_cash(definitions,resources):
    s = _create_initial_state(resources,definitions)
    assert len(s.resource_sites)==3 and s.cash.amount==1250
    assert {u.specialization for u in s.resource_sites.values()}=={'machine.extractor','machine.drilling','machine.agriculture'}
    assert all(u.building_investment==0 and u.slot_count==1 for u in s.resource_sites.values())
    assert len(s.cards)==8 and not s.installed_card_ids()|s.installed_freight_card_ids()
    assert sum(c.definition_id=='machine.extractor' for c in s.cards.values())==3
    assert not any(c.definition_id in {'machine.drilling','machine.agriculture'} for c in s.cards.values())
    assert all(production_facility_price(s,'resources',u.specialization)==4000 for u in s.resource_sites.values())
    raw=serialize_game_state(s)
    assert serialize_game_state(deserialize_game_state(raw))==raw and STATE_SCHEMA_VERSION==9


def test_legacy_single_site_load_never_runs_genesis(definitions,resources):
    s=_create_initial_state(resources,definitions)
    s.resource_sites.pop('site-2');s.resource_sites.pop('site-3')
    raw=serialize_game_state(s)
    for _ in range(3):raw=serialize_game_state(deserialize_game_state(raw))
    assert len(raw['resource_sites'])==1


@pytest.mark.parametrize('kind',['resources','factory','energy'])
def test_rename_changes_only_name(definitions,resources,kind):
    s=_create_initial_state(resources,definitions);unit=next(iter(s.production_units(kind).values()))
    before=deepcopy(s);RenameHall(unit.hall_id,'Renamed',kind).apply(s)
    assert unit.name=='Renamed'
    next(iter(before.production_units(kind).values())).name='Renamed'
    assert serialize_game_state(s)==serialize_game_state(before)


@pytest.mark.parametrize('target',['machine.extractor','machine.drilling','machine.agriculture','bad'])
def test_public_rename_cannot_retype_even_same_type(definitions,resources,target):
    s=_create_initial_state(resources,definitions);raw=serialize_game_state(s)
    with pytest.raises(ValueError):RenameHall('site-1','New','resources',target).apply(s)
    assert serialize_game_state(s)==raw


@pytest.mark.parametrize('case',['duplicate','stale-cost','stale-level','no-money'])
def test_storage_quote_is_revalidated_and_cannot_double_book(definitions,resources,case):
    s=_create_initial_state(resources,definitions);s.cash.amount=1e9
    level=s.inventory_storage_level;cost=inventory_storage_upgrade_cost(level)
    command=ExpandInventoryStorage(resources,level,cost)
    if case=='duplicate':command.apply(s)
    elif case=='stale-cost':command=ExpandInventoryStorage(resources,level,cost+.01)
    elif case=='stale-level':s.inventory_storage_level+=1
    elif case=='no-money':s.cash.amount=cost-.01
    before=serialize_game_state(s)
    with pytest.raises(ValueError):command.apply(s)
    assert serialize_game_state(s)==before


def test_group_install_uses_existing_commands_and_rejects_whole_bad_plan(definitions):
    from test_phase2_inventory_backend import company
    s=company(definitions);BuyCommonSupplyCard('machine.processor',definitions,2).apply(s)
    ids=tuple(s.cards)
    invalid=InstallInventoryCards(tuple(InstallCardInHall('h',0,cid,'factory') for cid in ids))
    raw=serialize_game_state(s)
    with pytest.raises(ValueError):invalid.apply(s)
    assert serialize_game_state(s)==raw
    group=InstallInventoryCards(tuple(InstallCardInHall('h',index,cid,'factory') for index,cid in enumerate(ids)))
    group.apply(s);assert set(ids)<=s.installed_card_ids()
    ReturnMachinesToInventory(ids).apply(s);group.apply(s);ReturnMachinesToInventory(ids).apply(s)
    cash=s.cash.amount;value=sum(resale_value(s.cards[cid],definitions[s.cards[cid].definition_id]) for cid in ids)
    SellMachines(ids,definitions).apply(s);assert s.cash.amount==cash+value
    raw=serialize_game_state(s)
    with pytest.raises((ValueError,KeyError)):SellMachines(ids,definitions).apply(s)
    assert serialize_game_state(s)==raw
