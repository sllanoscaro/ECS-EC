"""Explicit action catalog: authorization is deny-by-default, never inferred from HTTP verbs."""

from ecs_ec.identity.schemas import Principal

BASIC = frozenset({"session.read", "session.logout", "account.password.change"})
READ = frozenset({"consumption.read", "costs.read", "reports.read", "reports.generate"})
ADMIN = frozenset({"identity.accounts.read", "identity.accounts.manage", "administration.history.read",
                   "consumption.configuration.read", "consumption.configuration.manage",
                   "costs.configuration.read", "costs.configuration.manage", "costs.bills.manage",
                   "costs.calculations.create", "costs.comparisons.create"})
ACTIONS = BASIC | READ | ADMIN


def permissions(principal: Principal) -> frozenset[str]:
    """Return fixed human actions for the current role/mode; invalid/technical principals get none."""
    if not isinstance(principal, Principal) or principal.role not in {"operador", "administrador_tecnico"}:
        return frozenset()
    if principal.mode == "password_change_required":
        return BASIC
    if principal.mode != "normal":
        return frozenset()
    return BASIC | READ | (ADMIN if principal.role == "administrador_tecnico" else frozenset())


def allowed(principal, action: str, building_id) -> bool:
    """Require a trusted human principal, the configured building and an explicit current permission."""
    return isinstance(principal, Principal) and principal.building_id == building_id and action in permissions(principal)
