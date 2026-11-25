"""008 composition through009's module registry; install coordination before any future dispatcher is enabled."""

import asyncio
import os
from contextlib import asynccontextmanager

from ecs_ec.core.lifecycle import Module
from ecs_ec.identity.coordination import ParticipantRegistry
from ecs_ec.notifications.api import problem_response, router
from ecs_ec.notifications.audit import ACTIONS
from ecs_ec.notifications.identity_coordination import NotificationParticipant
from ecs_ec.notifications.repository import NotificationProblem
from ecs_ec.notifications.services import Notifications
from ecs_ec.notifications.settings import NotificationSettings


def install(app, identity, consumption):
    """Wire installed owners and frozen participant registry; this initial module has no mail loops."""
    existing = identity.participants.freeze()
    if not any(p.name == "notifications008" for p in existing):
        registry = ParticipantRegistry()
        for participant in existing:
            registry.register(participant)
        registry.register(NotificationParticipant(app.state.clock, identity.timezone))
        registry.freeze()
        identity.participants = registry
    try:
        options = NotificationSettings(
            environment=app.state.settings.environment,
            public_url=app.state.settings.public_url,
        )
        app.state.notification_configuration_invalid = False
    except ValueError:
        import os

        os.write(2, b"notification_disabled_invalid_configuration\n")
        safe = {
            name: field.get_default(call_default_factory=True)
            for name, field in NotificationSettings.model_fields.items()
        }
        safe.update(
            notification_enabled=False,
            environment="test",
            app_public_base_url=app.state.settings.public_url,
        )
        # Supply every field explicitly so optional mail cannot re-read a malformed
        # environment value and turn the fallback into a readiness blocker.
        options = NotificationSettings(_env_file=None, **safe)
        app.state.notification_configuration_invalid = True
    app.state.notifications = Notifications(
        app.state.database, app.state.clock, identity, consumption, options
    )
    identity.history_actions = identity.history_actions | ACTIONS
    app.add_exception_handler(NotificationProblem, problem_response)
    app.include_router(router)

    @asynccontextmanager
    async def lifespan(application):
        """Opt-in supervised jobs live inside the monolith; SMTP never participates in functional readiness."""
        app.state.notifications.telemetry = getattr(
            application.state, "telemetry", None
        )
        if not options.notification_enabled:
            yield
            return
        runner = Runner(app.state.notifications)
        runner.start()
        try:
            yield
        finally:
            await runner.close()

    return Module("notifications", lifespan=lifespan)


class Runner:
    """Supervise periodic materialization/recovery and SMTP independently with bounded retry cycles."""

    def __init__(self, service):
        """Create internal jobs without opening dependencies or starting an independent worker deployment."""
        from ecs_ec.notifications.dispatcher import Dispatcher
        from ecs_ec.notifications.episodes import Evaluator
        from ecs_ec.notifications.scheduler import Scheduler

        self.service = service
        self.scheduler = Scheduler(service)
        self.dispatcher = Dispatcher(service)
        self.evaluator = Evaluator(service)
        self.stop = asyncio.Event()
        self.wake = asyncio.Event()
        self.ready = asyncio.Event()
        self.tasks = []

    def start(self):
        """Install wakeup only after coordination/route registration; supervision retries failures without raw exceptions."""
        self.service.wake = self.wake
        self.tasks = [
            asyncio.create_task(self.schedule_loop(), name="notifications008-schedule"),
            asyncio.create_task(self.dispatch_loop(), name="notifications008-dispatch"),
            asyncio.create_task(self.evaluate_loop(), name="notifications008-evaluate"),
        ]

    async def pause(self):
        """Clock polling remains at most five seconds even when another consumer clears the shared wake signal."""
        if self.stop.is_set():
            return
        try:
            async with asyncio.timeout(
                self.service.settings.notification_cycle_seconds
            ):
                await self.wake.wait()
        except TimeoutError:
            pass
        self.wake.clear()

    async def schedule_loop(self):
        """Never enable dispatch before reconciliation; losing leadership stops planning until reacquired."""
        from ecs_ec.notifications.recovery import consolidate, reconcile_attempts

        while not self.stop.is_set():
            try:
                if await self.scheduler.acquire():
                    await reconcile_attempts(self.service)
                    await self.scheduler.tick()
                    await consolidate(self.service)
                    self.ready.set()
                else:
                    self.ready.set()  # A peer leader owns planning; durable dispatch remains safe.
            except Exception:
                self.ready.clear()
                os.write(2, b"notification_scheduler_cycle_failed\n")
                try:
                    await self.scheduler.close()
                except Exception:
                    pass
            await self.pause()

    async def dispatch_loop(self):
        """A saturated/failed SMTP relay delays only its bounded slots, never API readiness or business commits."""
        while not self.stop.is_set():
            try:
                if self.ready.is_set() and await self.dispatcher.dispatch_once():
                    continue
            except Exception:
                # A persistence failure after DATA intentionally leaves a durable open attempt.
                os.write(2, b"notification_dispatch_cycle_failed\n")
            await self.pause()

    async def evaluate_loop(self):
        """Read only committed functional events and evaluate silence by clock even without another reception or human session."""
        while not self.stop.is_set():
            try:
                if self.ready.is_set() and await self.evaluator.tick():
                    self.wake.set()
            except Exception:
                os.write(2, b"notification_evaluation_cycle_failed\n")
            await self.pause()

    async def close(self):
        """Stop new claims, join actual thread calls, then release process/scheduler session locks."""
        self.stop.set()
        self.wake.set()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        await self.dispatcher.close()
        await self.scheduler.close()
        self.service.wake = None
