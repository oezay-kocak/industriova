"""Paid MK1 templates. Validation completes before any cash, slot or cargo changes."""
from dataclasses import dataclass, field, replace
from uuid import uuid4
from production_zero.core.definitions import FreightDefinition, MachineDefinition
from production_zero.core.cards import create_card_instance
from production_zero.core.enums import Rarity
from production_zero.core.state import MachineProductionState


@dataclass(frozen=True, slots=True)
class MachineTemplate:
    definition_id: str
    production_id: str | None = None
    paused: bool = False
    route_resource: str | None = None
    route_destination: str | None = None


def copy_templates(state, card_ids):
    if not card_ids or len(set(card_ids)) != len(card_ids):
        raise ValueError('Select distinct installed machines or a populated line.')
    installed = {slot.card_id for unit in (*state.all_production_units(), *state.freight.facilities.values()) for slot in unit.slots if slot.card_id}
    if any(cid not in installed for cid in card_ids):
        raise ValueError('Only installed machines can be copied.')
    result=[]
    for cid in card_ids:
        card=state.cards[cid]; production=state.machine_production.get(cid); route=state.freight.assignments.get(cid)
        result.append(MachineTemplate(card.definition_id, production.selected_production_id if production else None,
                                      card.paused, route.resource_id if route else None, route.destination_kind if route else None))
    return tuple(result)


def quote_templates(state, definitions, templates, board_kind, unit_id, line_id):
    from production_zero.core.commands import _card_allowed_on_board
    from production_zero.core.machine_operations import site_accepts
    from production_zero.core.progression import production_options_for_machine
    from production_zero.core.production_pause import freight_line_number
    from production_zero.core.supply import common_card_price, _is_common_supply_definition
    if not templates or len(templates)>10000:
        raise ValueError('Copy machines or a populated line first.')
    if board_kind=='freight':
        unit=state.freight.facilities[unit_id]
        indexes=[slot.index for slot in unit.slots if slot.index in unit.unlocked_slot_indexes() and freight_line_number(unit,slot.index)==line_id]
        if not indexes:raise ValueError('Select an unlocked target line.')
    else:
        unit=state.production_units(board_kind)[unit_id]
        line=next((line for line in unit.production_lines if line.line_id==line_id and line.unlocked),None)
        if line is None:raise ValueError('Select an unlocked target line.')
        indexes=line.slot_indexes
    free=[i for i in indexes if unit.slots[i].card_id is None]
    total=0.; plans=[]
    for template in templates:
        definition=definitions.get(template.definition_id)
        if definition is None or not _is_common_supply_definition(definition):
            raise ValueError('Template machine is not available in Common Supply.')
        if board_kind=='freight':
            if not isinstance(definition,FreightDefinition) or definition.facility_id!=unit.facility_type:
                raise ValueError('Template requires a compatible freight facility.')
            if template.route_resource is not None and (template.route_resource not in state.resources or template.route_destination not in {'market','contract','consortium'}):
                raise ValueError('Copied route is no longer available.')
        else:
            probe=create_card_instance('probe',definition.definition_id,definition.card_kind,Rarity.COMMON)
            if not _card_allowed_on_board(probe,board_kind) or (board_kind=='resources' and not site_accepts(state,unit,definition.definition_id)):
                raise ValueError('Template requires a compatible production site.')
        option=None
        if template.production_id:
            if not isinstance(definition,MachineDefinition):raise ValueError('Invalid production template.')
            option=next((p for p in production_options_for_machine(state,definition) if p.production_id==template.production_id),None)
            if option is None:raise ValueError('Copied recipe must be unlocked at the destination.')
        price=common_card_price(definition);total+=price;plans.append((template,definition,option,price))
    if board_kind=='resources' and len({t.definition_id for t in templates})>1:
        raise ValueError('Resource sites accept one machine family.')
    return unit,free,round(total,2),plans


@dataclass(frozen=True, slots=True)
class PurchaseTemplates:
    templates: tuple[MachineTemplate,...]
    board_kind: str
    unit_id: str
    line_id: str | int
    definitions: dict
    expected_total: float
    operation_id: str = field(default_factory=lambda: uuid4().hex)

    def apply(self,state):
        from production_zero.core.freight import FreightAssignment
        from production_zero.core.supply import _check_operation, _check_price
        _check_operation(state, self.operation_id)
        unit,free,total,plans=quote_templates(state,self.definitions,self.templates,self.board_kind,self.unit_id,self.line_id)
        if total!=self.expected_total:raise ValueError('Purchase price changed. Review the quote again.')
        if len(free)<len(plans):raise ValueError(f'Requires {len(plans)} free slots; {len(free)} available.')
        cards=[replace(create_card_instance('machine-'+uuid4().hex,definition.definition_id,definition.card_kind,Rarity.COMMON),
                       acquisition_cost=price,paused=template.paused) for template,definition,option,price in plans]
        ids = {card.card_id for card in cards}
        if len(ids) != len(cards) or ids & state.cards.keys():
            raise ValueError("Purchase requires fresh unique card IDs.")
        _check_price(state, total / len(cards), len(cards))
        # All operations that can reject have completed before committing.
        state.cash.spend(total)
        for card,index,(template,definition,option,price) in zip(cards,free,plans):
            state.cards[card.card_id]=card;unit.slots[index].card_id=card.card_id
            if self.board_kind=='resources' and unit.specialization is None:unit.specialization=definition.definition_id
            if option is not None:
                state.machine_production[card.card_id]=MachineProductionState(card.card_id,option.output_resource,option.production_id)
            if self.board_kind=='freight' and template.route_resource is not None:
                state.freight.assignments[card.card_id]=FreightAssignment(template.route_resource,template.route_destination)
        state.completed_card_operations.add(self.operation_id)
        state.history.append('cash',state.cash.amount)
