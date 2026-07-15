#!/usr/bin/env python3
"""Client DEM: executa regras ativas e envia resultados ao backend."""

from __future__ import annotations

import argparse
import datetime as dt
import getpass
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from typing import Any

DEFAULT_API_BASE_URL = "http://127.0.0.1:3026"
DEFAULT_CLIENT_FIXED_TOKEN = "df991b67-24b2-4121-8c73-9c3ab4b0dba2"


def read_machine_id() -> str:
    machine_id_paths = ["/etc/machine-id", "/var/lib/dbus/machine-id"]
    for path in machine_id_paths:
        try:
            with open(path, "r", encoding="utf-8") as file:
                value = file.read().strip()
                if value:
                    return value
        except OSError:
            continue

    return f"unknown-{socket.gethostname()}"


def http_get_json(url: str, api_token: str) -> Any:
    request = urllib.request.Request(
        url,
        method="GET",
        headers={"x-api-token": api_token},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read().decode("utf-8")
        return json.loads(payload)


def http_post_json(url: str, body: dict[str, Any], api_token: str) -> Any:
    payload = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-api-token": api_token,
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        response_payload = response.read().decode("utf-8")
        return json.loads(response_payload) if response_payload else None


def normalize_output(stdout: str, stderr: str) -> str:
    pieces = []
    if stdout.strip():
        pieces.append(stdout.strip())
    if stderr.strip():
        pieces.append(stderr.strip())

    if not pieces:
        return ""

    return "\n".join(pieces)


def validate_output(output: str, validation_type: str, validation_value: str) -> bool:
    validation_type = (validation_type or "").strip().lower()
    validation_value = (validation_value or "").strip()

    if not validation_type or not validation_value:
        return True

    if validation_type == "exact":
        return output.strip() == validation_value

    if validation_type == "regex":
        return re.search(validation_value, output) is not None

    return False


def execute_rule(
    command: str, validation_type: str, validation_value: str
) -> tuple[str, str]:
    bash_path = shutil.which("bash")

    if bash_path:
        completed = subprocess.run(
            [bash_path, "-lc", command],
            check=False,
            capture_output=True,
            text=True,
        )
    else:
        completed = subprocess.run(
            command,
            shell=True,
            check=False,
            capture_output=True,
            text=True,
        )

    output = normalize_output(completed.stdout, completed.stderr)

    if completed.returncode != 0:
        return "error", output

    if not validate_output(output, validation_type, validation_value):
        return "error", output

    return "success", output


def run(api_base_url: str, api_token: str) -> int:
    machine_id = read_machine_id()
    machine_name = socket.gethostname()
    username = getpass.getuser()

    verifications_url = f"{api_base_url}/api/verifications/active"
    results_url = f"{api_base_url}/api/verification-results"

    try:
        rules = http_get_json(verifications_url, api_token)
    except urllib.error.URLError as error:
        print(format_url_error("Erro ao buscar regras ativas", error))
        return 0

    if not isinstance(rules, list):
        print("Resposta invalida ao buscar regras ativas.")
        return 1

    print(f"Regras ativas encontradas: {len(rules)}")

    for rule in rules:
        verification_id = rule.get("id")
        name = rule.get("name", "sem nome")
        command = rule.get("command", "")
        validation_type = rule.get("validationType", "")
        validation_value = rule.get("validationValue", "")

        if not verification_id or not command:
            print(f"Pulando regra invalida: {rule}")
            continue

        result, output = execute_rule(command, validation_type, validation_value)
        processed_at = dt.datetime.now(dt.timezone.utc).isoformat()

        payload = {
            "processedAt": processed_at,
            "machineId": machine_id,
            "username": username,
            "machineName": machine_name,
            "verificationId": int(verification_id),
            "result": result,
            "output": output,
        }

        try:
            http_post_json(results_url, payload, api_token)
            print(f"[{result.upper()}] {name}")
        except urllib.error.URLError as error:
            print(format_url_error(f"Falha ao enviar resultado da regra '{name}'", error))

    return 0


def format_url_error(prefix: str, error: Exception) -> str:
    details = getattr(error, "reason", None) or str(error)
    return f"{prefix}: nao foi possivel conectar na API ({details}). Encerrando sem sucesso."


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Executa regras ativas no DEM e envia resultados.",
    )
    parser.add_argument(
        "--API_BASE_URL",
        dest="api_base_url",
        default=DEFAULT_API_BASE_URL,
        help="URL base da API DEM (padrao: http://127.0.0.1:3026)",
    )
    parser.add_argument(
        "--CLIENT_FIXED_TOKEN",
        dest="client_fixed_token",
        default=DEFAULT_CLIENT_FIXED_TOKEN,
        help="Token fixo enviado no header x-api-token",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return run(args.api_base_url.rstrip("/"), args.client_fixed_token)


if __name__ == "__main__":
    sys.exit(main())
