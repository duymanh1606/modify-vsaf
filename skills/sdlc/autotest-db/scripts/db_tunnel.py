"""
SSH Tunnel helper for Robot Framework DB testing.
Copied to python_lib/db_tunnel.py in the project when tunnel is needed.

Usage in Robot Framework:
    Library    python_lib/db_tunnel.py    WITH NAME    DBTunnel
    DBTunnel.Open Tunnel    ssh_host=...    ssh_user=...    ssh_key=...    ...
    DBTunnel.Close Tunnel
"""

import threading


class db_tunnel:
    ROBOT_LIBRARY_SCOPE = "SUITE"

    def __init__(self):
        self._server = None

    def open_tunnel(
        self,
        ssh_host,
        ssh_user,
        remote_host,
        remote_port,
        local_port=13306,
        ssh_port=22,
        ssh_key=None,
        ssh_password=None,
    ):
        """Open an SSH tunnel. Binds remote_host:remote_port to localhost:local_port.

        Args:
            ssh_host:     SSH server hostname/IP (the jump host)
            ssh_user:     SSH username
            remote_host:  DB host as seen from the SSH server (often 127.0.0.1)
            remote_port:  DB port on the remote side (e.g. 3306)
            local_port:   Local port to bind (default: 13306, avoids conflict with local MySQL)
            ssh_port:     SSH port (default: 22)
            ssh_key:      Path to private key file (.pem / .ppk / id_rsa)
            ssh_password: Password-based auth (use ssh_key when possible)
        """
        try:
            from sshtunnel import SSHTunnelForwarder
        except ImportError:
            raise ImportError(
                "sshtunnel not installed. Run: pip install sshtunnel paramiko"
            )

        pkey_path = ssh_key if ssh_key else None
        password = ssh_password if ssh_password else None

        self._server = SSHTunnelForwarder(
            (ssh_host, int(ssh_port)),
            ssh_username=ssh_user,
            ssh_pkey=pkey_path,
            ssh_password=password,
            remote_bind_address=(remote_host, int(remote_port)),
            local_bind_address=("127.0.0.1", int(local_port)),
        )
        self._server.start()
        print(
            f"SSH tunnel open: {ssh_host} → {remote_host}:{remote_port} "
            f"via localhost:{local_port}"
        )

    def close_tunnel(self):
        """Close the SSH tunnel. Always call this in Suite Teardown after DB - Disconnect."""
        if self._server and self._server.is_active:
            self._server.stop()
            print("SSH tunnel closed.")
        self._server = None

    def get_local_port(self):
        """Return the local port the tunnel is bound to (useful for dynamic port assignment)."""
        if self._server:
            return self._server.local_bind_port
        raise RuntimeError("Tunnel is not open.")