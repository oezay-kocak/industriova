"""Resource price display; all economics stay in the existing central functions."""
from production_zero.core.market import market_price_for
from production_zero.core.modifiers import market_sale_price
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP, localcontext
from math import ulp

def price_number(value):
    """Display a unit price rounded up to a cent, without changing economics."""
    number = Decimal(str(value))
    if not number.is_finite():
        raise ValueError("A price must be finite.")
    with localcontext() as context:
        context.prec = max(28, len(number.as_tuple().digits) + abs(number.adjusted()) + 4)
        if isinstance(value, float):
            # A multiplication such as 1.1 * 1.1 can land one binary ULP
            # above an exact cent. Remove only that representation noise;
            # Decimal inputs and genuine fractional cents remain exact.
            cent = number.quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
            if abs(number - cent) <= Decimal(str(ulp(value))) * 2:
                number = cent
        return format(number.quantize(Decimal('.01'), rounding=ROUND_CEILING if number > 0 else ROUND_HALF_UP), ',.2f')

def base_price_text(resource_id, state=None, *, compact=False):
    value = market_price_for(state.market if state else None,resource_id)
    if compact:
        return f"BASE SELL ${price_number(value)}/U"
    return f"BASE SELL PRICE: ${price_number(value)} / UNIT"

def price_tooltip(state, resource_id):
    return base_price_text(resource_id,state) + "\n" + f"EFFECTIVE SELL PRICE: ${price_number(market_sale_price(state,resource_id))} / UNIT (current Research)\nUnit display rounds up to cents. Settlement uses precise unit values; total quotes show the booked amount."
