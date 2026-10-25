"""Formatting for the existing freight header and hover, without state writes."""
from production_zero.core.freight_statistics import DeliveryRate


def compact_rate(amount):
    if amount == 0:
        return '0/min'
    if amount < 0.01:
        return f'{amount:.3g}/min'
    for threshold, suffix in ((1e12,'T'),(1e9,'B'),(1e6,'M'),(1e3,'K')):
        if amount >= threshold:
            return f'{amount/threshold:.3g}{suffix}/min'
    return f'{amount:,.2f}'.rstrip('0').rstrip('.')+'/min'


def actual_throughput_text(rate: DeliveryRate):
    if rate.observing_seconds <= 0:
        return 'MEASURING…'
    amount = f'{rate.total:.3g}' if 0 < rate.total < 0.01 or rate.total >= 1e9 else f'{rate.total:,.2f}'
    suffix = f'\nMEASURING… {rate.observing_seconds:.0f}/60s' if rate.measuring else ''
    return f'{amount} units/min{suffix}'


def overview_tooltip(rate: DeliveryRate):
    rows = [f'{label}: {value:.12g} units/min' for label,value in (
        ('SELL',rate.sell),('CONTRACT',rate.contract),('CONSORTIUM',rate.consortium),('TOTAL',rate.total))]
    rows.append(f'Observed: {rate.observing_seconds:g}/60 simulation seconds')
    rows.append('Completed deliveries only; 1-second buckets, 60-second rolling window.')
    if rate.measuring:
        rows.append('MEASURING… Rates are normalized from the observed time.')
    return '\n'.join(rows)
