from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any
from urllib import request
from urllib.parse import urlencode


class TelegramClient:
    def __init__(self, token: str, timeout: int = 30):
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.timeout = timeout

    async def get_updates(self, offset: int | None = None) -> list[dict[str, Any]]:
        payload: dict[str, Any] = {
            "timeout": self.timeout,
            "allowed_updates": json.dumps(["message"]),
        }
        if offset is not None:
            payload["offset"] = offset
        response = await asyncio.to_thread(self._request_json, "getUpdates", payload)
        return list(response.get("result", []))

    async def send_message(self, chat_id: int, text: str) -> None:
        await asyncio.to_thread(
            self._request_json,
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
        )

    async def send_document(
        self,
        chat_id: int,
        filename: str,
        content: bytes,
        caption: str | None = None,
    ) -> None:
        await asyncio.to_thread(
            self._request_multipart,
            "sendDocument",
            fields={
                "chat_id": str(chat_id),
                "caption": caption or "",
            },
            file_field="document",
            filename=filename,
            content=content,
            content_type="image/svg+xml",
        )

    def _request_json(self, method: str, data: dict[str, Any]) -> dict[str, Any]:
        body = urlencode(data).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/{method}",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with request.urlopen(req, timeout=self.timeout + 5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not payload.get("ok"):
            raise RuntimeError(payload)
        return payload

    def _request_multipart(
        self,
        method: str,
        fields: dict[str, str],
        file_field: str,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> dict[str, Any]:
        boundary = uuid.uuid4().hex
        body = bytearray()

        for name, value in fields.items():
            body.extend(f"--{boundary}\r\n".encode("utf-8"))
            body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
            body.extend(value.encode("utf-8"))
            body.extend(b"\r\n")

        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            (
                f'Content-Disposition: form-data; name="{file_field}"; '
                f'filename="{filename}"\r\n'
                f"Content-Type: {content_type}\r\n\r\n"
            ).encode("utf-8")
        )
        body.extend(content)
        body.extend(b"\r\n")
        body.extend(f"--{boundary}--\r\n".encode("utf-8"))

        req = request.Request(
            f"{self.base_url}/{method}",
            data=bytes(body),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
        with request.urlopen(req, timeout=self.timeout + 5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not payload.get("ok"):
            raise RuntimeError(payload)
        return payload
