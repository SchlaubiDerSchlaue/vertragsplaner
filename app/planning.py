from datetime import date
from decimal import Decimal
import calendar
from app.models import Contract


def month_range(start_date, end_date):
    current = date(start_date.year, start_date.month, 1)
    end = date(end_date.year, end_date.month, 1)

    while current <= end:
        yield current

        if current.month == 12:
            current = date(current.year + 1, 1, 1)
        else:
            current = date(current.year, current.month + 1, 1)


def last_day_of_month(d):
    return date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


def contract_is_valid(contract, month_start, month_end, include_forecast=False):
    if contract.status == "draft":
        return False

    if contract.status == "forecast" and not include_forecast:
        return False

    if contract.status == "ended":
        return False

    if contract.start_date > month_end:
        return False

    if contract.end_date and contract.end_date < month_start:
        return False

    return True


def get_valid_version(position, month_start):
    versions = sorted(position.versions, key=lambda v: v.valid_from, reverse=True)

    for version in versions:
        if not version.is_active:
            continue

        if version.valid_from <= month_start and (
            version.valid_to is None or version.valid_to >= month_start
        ):
            return version

    return None


def recurrence_matches(version, month_start):
    if version.recurrence == "monthly":
        return True

    if version.recurrence == "quarterly":
        return month_start.month in [1, 4, 7, 10]

    if version.recurrence == "yearly":
        return month_start.month == version.valid_from.month

    if version.recurrence == "once":
        return (
            month_start.year == version.valid_from.year
            and month_start.month == version.valid_from.month
        )

    return False


def generate_planning_lines(
    start_date,
    end_date,
    include_revenue=True,
    include_cost=False,
    include_forecast=False,
):
    lines = []
    contracts = Contract.query.all()

    for contract in contracts:
        for month_start in month_range(start_date, end_date):
            month_end = last_day_of_month(month_start)

            if not contract_is_valid(contract, month_start, month_end, include_forecast):
                continue

            for position in contract.positions:
                if position.status != "active":
                    continue

                if position.position_type == "revenue" and not include_revenue:
                    continue

                if position.position_type == "cost" and not include_cost:
                    continue

                version = get_valid_version(position, month_start)

                if not version:
                    continue

                if not recurrence_matches(version, month_start):
                    continue

                amount = Decimal(version.amount)

                if position.position_type == "cost":
                    amount = -abs(amount)

                lines.append({
                    "month": month_start.strftime("%Y-%m"),
                    "partner": contract.partner_name,
                    "partner_type": contract.partner_type,
                    "customer": contract.partner_name,
                    "contract_no": contract.contract_no or "",
                    "contract": contract.title,
                    "contract_status": contract.status,
                    "position": position.name,
                    "type": position.position_type,
                    "amount": amount,
                    "currency": version.currency,
                    "account": version.account or "",
                    "cost_center_1": version.cost_center_1 or "",
                    "cost_center_2": version.cost_center_2 or "",
                })

    return lines
