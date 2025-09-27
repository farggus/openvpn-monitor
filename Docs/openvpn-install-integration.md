# Integrating `openvpn-install.sh` with OpenVPN Monitor

This project ships with the widely used community script [`openvpn-install.sh`](../openvpn-install.sh).
The script is designed for interactive command-line administration and it is **not** intended to be
invoked directly from the Flask web application. Nevertheless, you can orchestrate the script from
server-side automation to provision or revoke VPN profiles while continuing to rely on the monitor
for status visibility. This document outlines a safe integration strategy.

## Why you should not call the script from the browser

* `openvpn-install.sh` must run with `root` privileges, manages services, and edits files under
  `/etc`. Exposing it to the public web UI would be a critical security risk.
* The script is interactive: it expects prompts on stdin/stdout. Running it inside a HTTP request
  would block the request thread and lead to unreliable behaviour.
* It is not idempotent. Mistimed or concurrent executions could corrupt your VPN configuration.

## Recommended architecture

1. **Create a privileged backend helper.** Write a small service (e.g. a systemd unit or
   dedicated CLI) that runs on the same host as OpenVPN with root permissions. This helper is
   responsible for executing `openvpn-install.sh` with pre-recorded answers (see the `expect`
   example below) or using alternative management commands.
2. **Expose a controlled API.** Have the helper provide a hardened interface (for example a REST
   or gRPC endpoint bound to `localhost` behind authentication). The Flask application can talk to
   this API instead of invoking the shell script directly.
3. **Keep responsibilities separate.** The web UI continues to display status information by
   reading the OpenVPN status log. Provisioning and revocation are delegated to the helper.

## Automating the script with `expect`

When you do need to reuse the script, drive it with an automation tool so you can supply the prompt
responses programmatically. A minimal example for creating a client profile looks like this:

```tcl
#!/usr/bin/expect -f
set timeout -1
spawn sudo ./openvpn-install.sh
expect "OpenVPN is already installed." { send "1\r" }
expect "Please enter the name of the client" { send "$env(CLIENT_NAME)\r" }
expect "Do you want to protect the configuration file with a password" { send "1\r" }
expect eof
```

Place the script on the VPN host, set `CLIENT_NAME` as an environment variable, and call it from
your privileged helper. You can extend the `expect` workflow for revocation by choosing the
corresponding menu option.

## Surfacing client lists in the UI

Once the provisioning helper has generated or revoked profiles, OpenVPN will update the status file
(usually `/var/log/openvpn/status.log`). The monitor already parses this file via `/api/clients`.
If you want to show issued-but-not-connected profiles, maintain a separate registry (for example,
store the client metadata in a database when you create the profile) and expose it through an API
endpoint that the UI can render in a modal or table.

## Security considerations

* Restrict the helper API with strong authentication (mutual TLS, VPN-only access, or a private
  message queue) to avoid arbitrary code execution.
* Audit and log every provisioning action. The monitor's UI can display these logs alongside the
  connection history for traceability.
* Schedule the helper to run outside the Flask process. Never spawn the `openvpn-install.sh`
  subprocess directly from request handlers.

Following this pattern lets you keep the convenience of the community install script while ensuring
that your OpenVPN Monitor deployment remains secure and stable.
