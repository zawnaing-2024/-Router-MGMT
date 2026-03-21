from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import threading
import queue

from app.core.database import SessionLocal
from app.core.security import decrypt_password
from app.models import Router
from app.services import SSHService


class InteractiveShell:
    def __init__(self, ssh: SSHService):
        self.ssh = ssh
        self.channel = None
        self.output_queue = queue.Queue()
        self.running = True
        
        transport = ssh.client.get_transport()
        transport.set_keepalive(30)
        
        self.channel = transport.open_session()
        self.channel.get_pty()
        self.channel.invoke_shell()
        
        self.reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self.reader_thread.start()
    
    def _read_loop(self):
        while self.running and self.channel:
            try:
                if self.channel.recv_ready():
                    data = self.channel.recv(4096).decode('utf-8', errors='replace')
                    if data:
                        self.output_queue.put(data)
                else:
                    import time
                    time.sleep(0.05)
            except Exception:
                break
    
    def write(self, data: str):
        if self.channel and self.channel.active:
            self.channel.send(data)
    
    def get_output(self, timeout: float = 0.1) -> str:
        result = []
        while True:
            try:
                data = self.output_queue.get(timeout=timeout)
                result.append(data)
            except queue.Empty:
                break
        return ''.join(result)
    
    def close(self):
        self.running = False
        try:
            if self.channel:
                self.channel.close()
        except Exception:
            pass


terminal_sessions = {}


async def websocket_endpoint(websocket: WebSocket, router_id: int):
    db = SessionLocal()
    shell = None
    
    try:
        await websocket.accept()
        await websocket.send_text("\r\n\x1b[36mRouter MGMT Terminal\x1b[0m\r\n")
        await websocket.send_text("\x1b[33m══════════════════════════════════════\x1b[0m\r\n\r\n")
        
        router = db.query(Router).filter(Router.id == router_id).first()
        if not router:
            await websocket.send_text("\x1b[31mError: Router not found\x1b[0m\r\n")
            await websocket.close()
            return
        
        await websocket.send_text(f"\x1b[33mConnecting to {router.hostname} ({router.ip_address}:{router.port})...\x1b[0m\r\n")
        
        password = decrypt_password(router.password_encrypted) if router.password_encrypted else None
        
        ssh = SSHService(
            host=router.ip_address,
            port=router.port,
            username=router.username,
            password=password,
            ssh_key=router.ssh_key
        )
        
        loop = asyncio.get_event_loop()
        success, message = await loop.run_in_executor(None, ssh.connect)
        
        if not success:
            await websocket.send_text(f"\x1b[31mConnection failed: {message}\x1b[0m\r\n")
            await websocket.close()
            return
        
        await websocket.send_text("\x1b[32mSSH connected, initializing shell...\x1b[0m\r\n")
        
        if not success:
            await websocket.send_text(f"\x1b[31mConnection failed: {message}\x1b[0m\r\n")
            await websocket.close()
            return
        
        await websocket.send_text("\x1b[32mSSH connected, initializing shell...\x1b[0m\r\n")
        
        shell = InteractiveShell(ssh)
        terminal_sessions[router_id] = shell
        
        await asyncio.sleep(1)
        
        shell.write('\r')
        await asyncio.sleep(0.5)
        
        initial_output = shell.get_output()
        if initial_output:
            await websocket.send_text(initial_output)
        
        await websocket.send_text(f"\x1b[32m✓ Ready - Type commands and press Enter\x1b[0m\r\n\r\n")
        
        async def read_loop():
            while True:
                try:
                    output = shell.get_output(timeout=0.05)
                    if output:
                        await websocket.send_text(output)
                    await asyncio.sleep(0.05)
                except Exception:
                    break
        
        reader_task = asyncio.create_task(read_loop())
        
        try:
            while True:
                data = await websocket.receive_text()
                if shell and shell.running:
                    shell.write(data)
        except WebSocketDisconnect:
            pass
        finally:
            reader_task.cancel()
            if router_id in terminal_sessions:
                del terminal_sessions[router_id]
                
    except Exception as e:
        try:
            await websocket.send_text(f"\x1b[31mError: {str(e)}\x1b[0m\r\n")
        except Exception:
            pass
    finally:
        if shell:
            shell.close()
        db.close()
