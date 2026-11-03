"""003 SFTP-only listener with explicit channel EOF and explicit-vs-cleanup CLOSE tracking.

AsyncSSH2.24.1's stream/handler adapters are deliberately pinned: generic channel close
calls eof_received internally. The subclass checks connection_lost before trusting EOF,
and marks cleanup before library file closes. Contract tests must accompany upgrades.
"""
import asyncio
import logging
import os
import asyncssh
from asyncssh.stream import SSHServerStreamSession
from asyncssh.sftp import SFTPServerHandler,FXP_STATUS
from asyncssh.packet import UInt32,String
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError,InvalidHashError
from ecs_ec.acquisition.config import current_binding
from ecs_ec.acquisition.staging import Staging


def technical_call(telemetry,method,*args,**kwargs):
    """Call the real optional007 port with catalog-only fields; no technical failure may affect SFTP durability."""
    try:
        if telemetry:return getattr(telemetry,method)(*args,**kwargs)
    except Exception:pass


class VirtualFiles(asyncssh.SFTPServer):
    """Expose only new session-local native files and a reserved probe, never the host filesystem."""
    def __init__(self,channel,staging):
        """Receive a trusted staging instance after authentication and durable session allocation."""
        super().__init__(channel)
        self.staging=staging

    def map_path(self,path):
        """Deny every inherited filesystem operation not explicitly implemented by this virtual server."""
        raise asyncssh.SFTPPermissionDenied('operation_not_permitted')

    async def open(self,path,pflags,attrs):
        """Require new, exclusive, write-only files; append/read/truncate modes cannot modify evidence."""
        allowed=asyncssh.FXF_WRITE|asyncssh.FXF_CREAT|asyncssh.FXF_EXCL
        if pflags!=allowed:
            self.staging.failed=True
            raise asyncssh.SFTPPermissionDenied('exclusive_write_required')
        try:return await self.staging.open(path)
        except Exception:
            raise asyncssh.SFTPFailure('acquisition_operation_rejected') from None

    async def write(self,file_obj,offset,data):
        """Delegate ordered offsets and quotas; return only a fixed safe failure to the client."""
        try:await self.staging.write(file_obj,offset,data)
        except Exception:raise asyncssh.SFTPFailure('acquisition_operation_rejected') from None

    async def close(self,file_obj):
        """Durably close explicit client handles, while cleanup remains distinguishable."""
        try:await self.staging.close(file_obj)
        except Exception:raise asyncssh.SFTPFailure('acquisition_operation_rejected') from None

    async def fsync(self,file_obj):
        """Flush only this open private handle; CLOSE performs the same durability check unconditionally."""
        file_obj.stream.flush();os.fsync(file_obj.stream.fileno())

    def fstat(self,file_obj):
        """Report only the current session handle's size and fixed permissions."""
        return asyncssh.SFTPAttrs(size=file_obj.offset,permissions=0o100600)

    def stat(self,path):
        """Expose the virtual directory only, without looking up host paths or old publications."""
        decoded=path.decode() if isinstance(path,bytes) else path
        if decoded in ('.','/',self.staging.binding.directory.rstrip('/') or '/'):
            return asyncssh.SFTPAttrs(permissions=0o40700)
        raise asyncssh.SFTPNoSuchFile('session_file_not_found')

    def lstat(self,path):
        """Use the virtual directory contract; symlinks are never exposed."""
        return self.stat(path)

    def realpath(self,path):
        """Resolve only the configured virtual root, with no OS path normalization."""
        self.stat(path)
        return self.staging.binding.directory.encode()

    def remove(self,path):
        """Permit deleting only the reserved probe, whose bytes are removed at CLOSE."""
        if self.staging.name(path)!='.ecs-ec-probe':
            self.staging.failed=True
            raise asyncssh.SFTPPermissionDenied('immutable_native_file')

    async def exit(self):
        """Finalize after all packet processing/cleanup; never promote on a generic channel exit."""
        await self.staging.finish()


class BatchHandler(SFTPServerHandler):
    """Pin packet/cleanup semantics so invalid operations and implicit CLOSEs cannot produce a sealed batch."""
    def send_packet(self,pkttype,pktid,*parts):
        """Observe protocol failure and replace arbitrary library exception text with a fixed code."""
        if pkttype==FXP_STATUS and parts:
            status=int.from_bytes(parts[-1][:4],'big')
            if status:
                self._server.staging.failed=True
                parts=(*parts[:-1],UInt32(status)+String('acquisition_operation_rejected')+String(''))
        return super().send_packet(pkttype,pktid,*parts)

    async def _cleanup(self,exc):
        """Mark library cleanup before it closes any still-open handle; such handles are not client CLOSEs."""
        self._server.staging.cleanup=True
        if self._file_handles or exc:
            self._server.staging.failed=True
        await super()._cleanup(exc)


class BatchSession(SSHServerStreamSession):
    """SFTP subsystem only; a connection-lost synthetic EOF is never a clean protocol EOF."""
    def __init__(self,staging,tasks,telemetry=None):
        """Bind one already-authorized durable staging session and no shell/exec factory."""
        super().__init__(None,sftp_factory=lambda channel:VirtualFiles(channel,staging),sftp_version=3)
        self.staging,self.tasks=staging,tasks
        self.telemetry=telemetry

    def eof_received(self):
        """Record only the channel's actual EOF callback, excluding the superclass disconnect cleanup path."""
        if not self._connection_lost:
            self.staging.clean_eof=True
        return super().eof_received()

    def session_started(self):
        """Run the pinned SFTP handler which distinguishes explicit CLOSE from its own cleanup."""
        async def run():
            """Allocate durable receiving state only after an actual SFTP subsystem was accepted."""
            handle=technical_call(self.telemetry,'begin','acquisition.receive','acquisition')
            outcome='success'
            try:
                await self.staging.start()
                technical_call(self.telemetry,'stage',handle,'authenticate')
                server=self._init_sftp_server()
                reader=asyncssh.SSHReader(self,self._chan)
                writer=asyncssh.SSHWriter(self,self._chan)
                await BatchHandler(server,reader,writer,3).run()
                technical_call(self.telemetry,'stage',handle,'transfer')
                publication=await self.staging.finish()
                outcome='success' if publication else 'expected_rejection'
                technical_call(self.telemetry,'stage',handle,'seal',outcome=outcome)
            except Exception:
                outcome='unexpected_error'
                self.staging.failed=True
                if self.staging.started:await self.staging.finish()
                self._chan.close()
            finally:
                technical_call(self.telemetry,'complete',handle,outcome=outcome,code='ok' if outcome=='success' else 'processing_interrupted')
        task=self._conn.create_task(run())
        self.tasks.add(task);task.add_done_callback(self.tasks.discard)



class TechnicalServer(asyncssh.SSHServer):
    """Authenticate technical binding identities without cookies, human accounts or functional role grants."""
    def __init__(self,database,clock,settings,credentials,connections,tasks,telemetry=None):
        """Capture private deployment credential material in memory, never in ledger or reports."""
        self.database,self.clock,self.settings,self.credentials=database,clock,settings,credentials
        self.binding=None;self.auth={}
        self.connections,self.tasks=connections,tasks
        self.connection=None
        self.telemetry=telemetry

    def connection_made(self,connection):
        """Track the accepted SSH connection so application shutdown can terminate unsealed work safely."""
        self.connection=connection;self.connections.add(connection)

    def connection_lost(self,error):
        """Release only the connection reference; channel cleanup owns session durability."""
        self.connections.discard(self.connection)

    async def begin_auth(self,username):
        """Resolve only the latest enabled trusted binding and matching protected credential record."""
        self.binding=await current_binding(self.database,username)
        self.auth=self.credentials.get(username,{}) if self.binding else {}
        return True

    def password_auth_supported(self):
        """Offer password verification only when an externally provisioned Argon2 verifier exists."""
        return bool(self.auth.get('password_hash'))

    async def validate_password(self,username,password):
        """Verify off the event loop, with no plaintext persistence or reflected authentication diagnostics."""
        try:
            return bool(self.binding) and await asyncio.to_thread(PasswordHasher().verify,self.auth['password_hash'],password)
        except (VerificationError,InvalidHashError,KeyError):return False

    def public_key_auth_supported(self):
        """Offer only keys declared in the binding's protected deployment auth record."""
        return bool(self.auth.get('public_keys'))

    def validate_public_key(self,username,key):
        """Match exact authorized public key material, never accept an unknown key from the client."""
        try:return any(asyncssh.import_public_key(item).public_data==key.public_data for item in self.auth.get('public_keys',()))
        except (ValueError,TypeError):return False

    async def session_requested(self):
        """Allocate an authenticated SFTP batch; every shell/exec/unknown subsystem remains denied."""
        if not self.binding:return False
        staging=Staging(self.database,self.clock,self.settings,self.binding)
        return BatchSession(staging,self.tasks,self.telemetry)


async def start_listener(database,clock,settings,telemetry=None):
    """Start the in-process listener with a persistent protected host key; caller owns close/wait_closed."""
    if not settings.host_key_file.is_file() or settings.host_key_file.stat().st_mode&0o077:
        raise ValueError('protected_host_key_required')
    # Vendor debug messages include remote identity/path details; use only the safe007 producer adapter.
    vendor=logging.getLogger('asyncssh')
    vendor.handlers=[logging.NullHandler()];vendor.propagate=False;vendor.setLevel(logging.CRITICAL)
    credentials=settings.credentials()
    connections,tasks=set(),set()
    server=await asyncssh.create_server(lambda:TechnicalServer(database,clock,settings,credentials,connections,tasks,telemetry),
        settings.sftp_host,settings.sftp_port,server_host_keys=[str(settings.host_key_file)],encoding=None,
        kex_algs=['curve25519-sha256','ecdh-sha2-nistp256'],encryption_algs=['aes256-ctr','aes128-ctr'],
        mac_algs=['hmac-sha2-256','hmac-sha2-512'],login_timeout=30)

    return Listener(server,connections,tasks)


class Listener:
    """Own listening socket plus every accepted channel/task, including interrupted shutdown cleanup."""
    def __init__(self,server,connections,tasks):
        """Retain only resources for this one listener; no unrelated process is stopped on close."""
        self.server,self.connections,self.tasks=server,connections,tasks

    def get_port(self):
        """Return the actual bound port, including OS-assigned ephemeral test ports."""
        return self.server.get_port()

    def close(self):
        """Stop admission and abort every still-active SSH connection without synthesizing a clean EOF."""
        self.server.close()
        for connection in tuple(self.connections):connection.abort()

    async def wait_closed(self):
        """Join socket, accepted connections and pending003 cleanup before the shared DB is disposed."""
        await self.server.wait_closed()
        await asyncio.gather(*(connection.wait_closed() for connection in tuple(self.connections)),return_exceptions=True)
        if self.tasks:await asyncio.gather(*tuple(self.tasks),return_exceptions=True)
