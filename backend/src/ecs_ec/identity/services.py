"""Identity orchestration: ordered DB locks, live authorization and atomic account evidence."""

from dataclasses import replace
from uuid import uuid4

from sqlalchemy import func, or_, select, tuple_
from sqlalchemy.exc import IntegrityError

from ecs_ec.core.unit_of_work import UnitOfWork
from ecs_ec.identity.audit import ACTIONS as HISTORY_ACTIONS, IdentityAudit
from ecs_ec.identity.coordination import ParticipantRegistry
from ecs_ec.identity.credentials import Credentials, normalize_email
from ecs_ec.identity.errors import IdentityProblem
from ecs_ec.identity.models import Account, Guard, Session
from ecs_ec.identity.permissions import ACTIONS, BASIC, READ, ADMIN, allowed
from ecs_ec.identity.schemas import AccountPage, AccountView, IdentityMutation, Principal, Recipient
from ecs_ec.identity.pagination import decode_cursor, encode_cursor
from ecs_ec.identity.repository import account_view


def recipient_eligible(account, required):
    """Evaluate current human role/state/renewal against every fixed requested permission, without a session."""
    if account is None or account.status != "active" or account.must_change_password or account.role not in {"operador", "administrador_tecnico"}:
        return False
    available = BASIC | READ | (ADMIN if account.role == "administrador_tecnico" else frozenset())
    return all(action in available for action in required)


class Identity:
    """Human identity facade; shared infrastructure remains owned by platform009."""

    def __init__(self, database, settings, clock, timezone, participants=None, history_actions=()):
        """Inject core resources and a composition-time participant registry; never load consumers."""
        self.database, self.settings, self.clock, self.timezone = database, settings, clock, timezone
        self.participants = participants or ParticipantRegistry()
        self.participants.freeze()
        self.audit = IdentityAudit(clock, timezone)
        self.credentials = Credentials(settings.hash_concurrency)
        # Installed producers may register their administrative codes at composition;
        # no import or alternate store of their domain is needed to read common evidence.
        self.history_actions = HISTORY_ACTIONS | frozenset(history_actions)

    async def resolve_session(self, bearer, *, action="session.read", activity="background"):
        """Resolve/authorize a fresh request through the durable session adapter, retaining no locks."""
        from ecs_ec.identity.sessions import resolve
        return await resolve(self, bearer, action=action, activity=activity)

    async def login(self, email, password, preauth_cookie, origin):
        """Authenticate with durable rolling wait and an independently consumed CSRF presession."""
        from ecs_ec.identity.sessions import login
        return await login(self, email, password, preauth_cookie, origin)

    async def bootstrap(self, email, password):
        """Create the first active administrator only in an empty guarded installation."""
        email, key = normalize_email(email, self.settings.environment != "production")
        encoded = await self.credentials.hash(password)
        return await self._mutate(operation="bootstrap", actor="process:bootstrap", email=email, email_key=key,
                                  role="administrador_tecnico", status="active", prepared_hash=encoded)

    async def recover_admin(self, email, password, reason):
        """Host-only recovery of an already active admin; validate bounded reason, capture revision before hashing."""
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 500 or any(ord(char) < 32 or ord(char) == 127 for char in reason):
            raise IdentityProblem("invalid_input", 422)
        _, key = normalize_email(email, self.settings.environment != "production")
        operation_ref = uuid4()
        async with UnitOfWork(self.database.sessions) as uow:
            snapshot = await uow.session.scalar(select(Account).where(Account.email_key == key))
            if snapshot:
                uow.session.expunge(snapshot)
        if snapshot is None or snapshot.role != "administrador_tecnico" or snapshot.status != "active":
            problem = IdentityProblem("recovery_not_allowed", 422, operation_ref=operation_ref)
            await self.rejection(actor="process:recovery", action="identity.recovery", target_id=snapshot.id if snapshot else None,
                                  problem=problem, operation_ref=operation_ref)
            raise problem
        encoded = await self.credentials.hash(password)
        return await self._mutate(operation="recover", actor="process:recovery", target_id=snapshot.id,
            expected_revision=snapshot.revision, prepared_hash=encoded, operation_ref=operation_ref)

    async def change_password(self, principal, current_password, new_password, *, operation_ref=None):
        """Verify current/exactly distinct password off-lock, then revalidate captured revision and original session."""
        self.authorize(principal, "account.password.change", self.settings.building_id)
        async with UnitOfWork(self.database.sessions) as uow:
            snapshot = await uow.session.get(Account, principal.account_id)
            if snapshot:
                uow.session.expunge(snapshot)
        if snapshot is None or not await self.credentials.verify(current_password, snapshot.password_hash):
            raise IdentityProblem("current_password_invalid", 422)
        if current_password == new_password:
            raise IdentityProblem("password_unchanged", 422)
        encoded = await self.credentials.hash(new_password)
        return await self._mutate(operation="password", actor=principal, target_id=principal.account_id,
                                  expected_revision=snapshot.revision, prepared_hash=encoded, operation_ref=operation_ref)

    async def create_account(self, principal, command, *, operation_ref=None):
        """Prepare a validated credential off-lock, then create with renewal and atomic evidence."""
        self.authorize(principal, "identity.accounts.manage", self.settings.building_id)
        email, key = normalize_email(command.email, self.settings.environment != "production")
        encoded = await self.credentials.hash(command.initial_password.get_secret_value())
        return await self._mutate(operation="create", actor=principal, email=email, email_key=key,
            role=command.role, status=command.status, prepared_hash=encoded, operation_ref=operation_ref)

    async def update_account(self, principal, target_id, command, expected_revision, *, operation_ref=None):
        """Edit current email/role/state under the original actor/session and revision locks."""
        self.authorize(principal, "identity.accounts.manage", self.settings.building_id)
        email, key = normalize_email(command.email, self.settings.environment != "production")
        return await self._mutate(operation="update", actor=principal, target_id=target_id, email=email,
            email_key=key, role=command.role, status=command.status, expected_revision=expected_revision, operation_ref=operation_ref)

    async def reset_account(self, principal, target_id, new_password, expected_revision, *, operation_ref=None):
        """Reset only another account, with a new initial credential and complete revocation."""
        self.authorize(principal, "identity.accounts.manage", self.settings.building_id)
        if principal.account_id == target_id:
            raise IdentityProblem("use_own_password_change", 422)
        encoded = await self.credentials.hash(new_password)
        return await self._mutate(operation="reset", actor=principal, target_id=target_id,
            expected_revision=expected_revision, prepared_hash=encoded, operation_ref=operation_ref)

    async def resolve_recipient(self, account_id, required_permissions):
        """Read a current internal recipient projection without cookies, notifications or human-session assumptions."""
        from uuid import UUID
        if not isinstance(account_id, UUID):
            raise IdentityProblem("invalid_input", 422)
        async with UnitOfWork(self.database.sessions) as uow:
            account = await uow.session.get(Account, account_id)
            if account is None:
                return Recipient(account_id, None, None, None, None, None, None, False)
            return Recipient(account.id, account.email, account.role, account.status, account.must_change_password,
                             account.auth_version, account.revision, recipient_eligible(account, required_permissions))

    async def list_accounts(self, principal, *, role=None, status=None, cursor=None, limit=25):
        """List approved projections ordered by creation/UUID, using signed filter-bound continuation."""
        from datetime import datetime
        from uuid import UUID
        self.authorize(principal, "identity.accounts.read", self.settings.building_id)
        if not 1 <= limit <= 100:
            raise IdentityProblem("invalid_input", 422)
        filters = {"role": role, "status": status}
        query = select(Account)
        if role is not None:
            query = query.where(Account.role == role)
        if status is not None:
            query = query.where(Account.status == status)
        if cursor:
            try:
                last = decode_cursor(self.settings, cursor, "accounts", filters)
                query = query.where(tuple_(Account.created_at, Account.id) > tuple_(datetime.fromisoformat(last["at"]), UUID(last["id"])))
            except (ValueError, KeyError, TypeError):
                raise IdentityProblem("invalid_input", 422) from None
        async with UnitOfWork(self.database.sessions) as uow:
            rows = (await uow.session.scalars(query.order_by(Account.created_at, Account.id).limit(limit+1))).all()
            selected = rows[:limit]
            continuation = encode_cursor(self.settings, "accounts", filters, {"at": selected[-1].created_at.isoformat(), "id": str(selected[-1].id)}) if len(rows) > limit else None
            return AccountPage(items=[account_view(row) for row in selected], next_cursor=continuation)

    async def get_account(self, principal, account_id):
        """Authorize before resolving an account and return only its public administrative projection."""
        self.authorize(principal, "identity.accounts.read", self.settings.building_id)
        async with UnitOfWork(self.database.sessions) as uow:
            row = await uow.session.get(Account, account_id)
            if row is None:
                raise IdentityProblem("not_found", 404)
            return account_view(row)

    def authorize(self, principal, action, building_id):
        """Apply fixed policy to this request's principal; future durable phases must re-resolve."""
        if not isinstance(principal, Principal):
            raise IdentityProblem("session_required", 401)
        if principal.mode == "password_change_required" and action not in {"session.read", "session.logout", "account.password.change"}:
            raise IdentityProblem("password_change_required", 403)
        if not allowed(principal, action, building_id):
            raise IdentityProblem("forbidden", 403)

    def require_report_access(self, principal, building_id):
        """Recheck reports.read without granting administrative mutation permissions."""
        self.authorize(principal, "reports.read", building_id)

    def session_valid(self, account, session, now):
        """Evaluate current rows using a newly acquired time after locks; equality already expires."""
        return account is not None and session is not None and account.status == "active" and (
            account.role in {"operador", "administrador_tecnico"} and session.account_id == account.id
            and session.revoked_at is None and session.auth_version == account.auth_version
            and session.csrf_key_id == self.settings.csrf_key_id
            and now < session.absolute_expires_at and now < session.idle_expires_at
            and session.mode == ("password_change_required" if account.must_change_password else "normal"))

    async def rejection(self, *, actor, action, target_id, problem, operation_ref):
        """After rollback, resolve any HTTP actor afresh and persist exactly one safe attempt."""
        from ecs_ec.audit.models import AuditRecord
        actor_ref = actor if isinstance(actor, str) else "unauthenticated"
        async with UnitOfWork(self.database.sessions) as uow:
            # The same guard resolves an uncertain preceding account commit before
            # checking evidence. Never append a second rejected record after an
            # already-committed allowed record with this operation reference.
            await uow.session.scalar(select(Guard).where(Guard.id == 1).with_for_update())
            existing = await uow.session.scalar(select(AuditRecord.id).where(
                AuditRecord.safe_payload["operation_ref"].astext == str(operation_ref)).limit(1))
            if existing is not None:
                problem.audited = True
                problem.operation_ref = operation_ref
                return
            if isinstance(actor, Principal):
                account = await uow.session.get(Account, actor.account_id)
                session = await uow.session.get(Session, actor.session_id)
                if self.session_valid(account, session, self.clock.now()):
                    actor_ref = "account:" + str(account.id)
            await self.audit.attempt(uow, actor_ref=actor_ref, action=action, target_id=target_id,
                result="denied" if problem.status in {401, 403} else "rejected", reason_code=problem.code,
                operation_ref=operation_ref)
            await uow.commit()
        problem.audited = True
        problem.operation_ref = operation_ref

    async def _mutate(self, *, operation, actor, target_id=None, email=None, email_key=None, role=None,
                      status=None, prepared_hash=None, expected_revision=None, operation_ref=None):
        """Coordinate one account mutation; retry changed participant sets at most three times.

        Argon2 is prepared by callers outside locks. All account paths, including CLI and
        self password changes, take guard→before resources→UUID accounts→UUID sessions→after.
        Any failure rolls back adjustments before a separate safe rejection is recorded.
        """
        operation_ref = operation_ref or uuid4()
        target_id = target_id or uuid4()
        action = {"create": "identity.account.created", "bootstrap": "identity.bootstrap",
                  "update": "identity.account.updated", "reset": "identity.account.reset",
                  "password": "identity.password.changed", "recover": "identity.recovery"}[operation]
        try:
            for attempt in range(3):
                async with UnitOfWork(self.database.sessions) as uow:
                    guard = await uow.session.scalar(select(Guard).where(Guard.id == 1).with_for_update())
                    if guard is None:
                        raise IdentityProblem("identity_unavailable", 503)
                    creating = operation in {"create", "bootstrap"}
                    original = None if creating else await uow.session.get(Account, target_id)
                    if operation == "bootstrap" and await uow.session.scalar(select(func.count()).select_from(Account)):
                        raise IdentityProblem("bootstrap_not_empty", 409)
                    if not creating and original is None:
                        raise IdentityProblem("not_found", 404)
                    next_role = role or (original.role if original else "administrador_tecnico")
                    next_status = status or (original.status if original else "active")
                    renewal = operation != "password" if creating or prepared_hash else original.must_change_password
                    fields = ("email", "role", "status", "credential", "renewal") if creating else tuple(
                        name for name, changed in (
                            ("email", email is not None and email != original.email),
                            ("role", next_role != original.role), ("status", next_status != original.status),
                            ("credential", prepared_hash is not None), ("renewal", renewal != original.must_change_password),
                        ) if changed)
                    actor_ref = "account:" + str(actor.account_id) if isinstance(actor, Principal) else actor
                    mutation = IdentityMutation(target_id, expected_revision, fields, next_role, next_status,
                                                renewal, actor_ref, operation_ref)
                    plans = await self.participants.discover(mutation, uow)
                    await self.participants.lock(plans, "before", uow)
                    account_ids = {target_id} | ({actor.account_id} if isinstance(actor, Principal) else set())
                    accounts = {row.id: row for row in (await uow.session.scalars(select(Account).where(
                        Account.id.in_(account_ids)).order_by(Account.id).with_for_update().execution_options(populate_existing=True))).all()}
                    original = accounts.get(target_id)
                    session_filter = Session.account_id == target_id
                    if isinstance(actor, Principal):
                        session_filter = or_(session_filter, Session.id == actor.session_id)
                    sessions = (await uow.session.scalars(select(Session).where(session_filter).order_by(
                        Session.id).with_for_update().execution_options(populate_existing=True))).all()
                    await self.participants.lock(plans, "after", uow)
                    now = self.clock.now()
                    if isinstance(actor, Principal):
                        account = accounts.get(actor.account_id)
                        session = next((row for row in sessions if row.id == actor.session_id), None)
                        if not self.session_valid(account, session, now):
                            raise IdentityProblem("session_required", 401)
                        current = Principal.from_rows(account, session, self.settings.building_id)
                        self.authorize(current, "account.password.change" if operation == "password" else "identity.accounts.manage", self.settings.building_id)
                        if operation == "password" and target_id != actor.account_id:
                            raise IdentityProblem("forbidden", 403)
                    elif actor not in {"process:bootstrap", "process:recovery"} or operation not in {"bootstrap", "recover"}:
                        raise IdentityProblem("forbidden", 403)
                    if not creating and expected_revision != original.revision:
                        raise IdentityProblem("revision_conflict", 412)
                    if operation == "recover" and (original.role != "administrador_tecnico" or original.status != "active"):
                        raise IdentityProblem("recovery_not_allowed", 422)
                    if operation == "reset" and target_id == actor.account_id:
                        raise IdentityProblem("use_own_password_change", 422)
                    if original and original.role == "administrador_tecnico" and original.status == "active" and (
                        next_role != "administrador_tecnico" or next_status != "active"):
                        count = await uow.session.scalar(select(func.count()).select_from(Account).where(
                            Account.role == "administrador_tecnico", Account.status == "active"))
                        if count <= 1:
                            raise IdentityProblem("last_active_administrator", 409)
                    if not await self.participants.stable(mutation, plans, uow):
                        continue
                    if isinstance(actor, Principal):
                        # An authorized mutation is activity, including a valid no-op. The
                        # original session is already locked and was checked with fresh time.
                        from datetime import timedelta
                        session = next(row for row in sessions if row.id == actor.session_id)
                        session.last_activity_at = max(session.last_activity_at, now)
                        session.idle_expires_at = min(session.absolute_expires_at, session.last_activity_at+timedelta(minutes=30))
                    if not fields:
                        await uow.commit()
                        return original
                    if creating:
                        original = Account(id=target_id, email=email, email_key=email_key, role=next_role, status=next_status,
                            password_hash=prepared_hash, must_change_password=True, auth_version=1, revision=1,
                            created_at=now, updated_at=now, password_changed_at=now, created_by=actor_ref, updated_by=actor_ref)
                        uow.session.add(original)
                    else:
                        original.email = email if email is not None else original.email
                        original.email_key = email_key if email_key is not None else original.email_key
                        original.role, original.status = next_role, next_status
                        original.must_change_password = renewal
                        original.revision += 1
                        original.auth_version += 1
                        original.updated_at, original.updated_by = now, actor_ref
                        if prepared_hash:
                            original.password_hash, original.password_changed_at = prepared_hash, now
                        for session in sessions:
                            if session.account_id == target_id and session.revoked_at is None:
                                session.revoked_at = now
                                session.revocation_code = "credential_changed" if prepared_hash else "account_changed"
                    await uow.session.flush()
                    await self.participants.apply(mutation, plans, uow)
                    await self.audit.changed(uow, account_id=original.id, revision=original.revision, actor_ref=actor_ref,
                        action=action, fields=fields, role=original.role, status=original.status,
                        renewal=original.must_change_password, operation_ref=operation_ref, administrative=operation != "password",
                        reason_code="operational_recovery" if operation == "recover" else "changed")
                    await uow.commit()
                    return original
            raise IdentityProblem("identity_coordination_retry", 409)
        except IntegrityError:
            problem = IdentityProblem("email_conflict", 409, operation_ref=operation_ref)
            await self.rejection(actor=actor, action=action, target_id=target_id, problem=problem, operation_ref=operation_ref)
            raise problem from None
        except IdentityProblem as problem:
            await self.rejection(actor=actor, action=action, target_id=target_id, problem=problem, operation_ref=operation_ref)
            raise
        except Exception:
            problem = IdentityProblem("identity_unavailable", 503, operation_ref=operation_ref)
            await self.rejection(actor=actor, action=action, target_id=target_id, problem=problem, operation_ref=operation_ref)
            raise problem from None
