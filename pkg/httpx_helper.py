import mimetypes
import os
import time
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException, status
from pkg.logger_helper import logger


class HTTPXClient:
    """
    基于 httpx 封装的工具类，GET/POST/PUT/DELETE 均接收完整 URL，
    自动处理 JSON、form-data、文件上传，以及错误转换为 HTTPException。
    """

    def __init__(self, timeout: int = 10, headers: dict[str, str] | None = None):
        """
        :param timeout: 请求超时时间，默认 10 秒
        :param headers: 公共请求头，默认 {'content-type': 'application/json'}
        """
        self.timeout = timeout
        self.headers = headers or {'content-type': 'application/json'}

    async def _request(
            self,
            method: str,
            url: str,
            *,
            params: dict[str, Any] | None = None,
            data: dict[str, Any] | str | None = None,
            json: dict[str, Any] | None = None,
            files: dict[str, Any] | None = None,
            headers: dict[str, str] | None = None,
            timeout: int | None = None,
    ) -> httpx.Response:
        """
        :param method: HTTP 方法
        :param url: 完整 URL
        :param params: 查询参数
        :param data: form-data 或普通 body
        :param json: JSON body
        :param files: 文件上传 dict, e.g. {'file': ('a.txt', b'bytes', 'text/plain')}
        :param headers: 单次请求头
        :param timeout: 单次请求超时
        """
        try:
            combined_headers = {**self.headers, **(headers or {})}
            if files:
                combined_headers.pop('content-type', None)  # 让 httpx 自动设置 multipart/form-data

            async with httpx.AsyncClient(timeout=timeout or self.timeout) as client:
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    params=params,
                    data=None if files else data,
                    json=None if files else json,
                    files=files,
                    headers=combined_headers,
                )
                response.raise_for_status()
                return response

        except httpx.HTTPStatusError as exc:
            logger.error(f"HTTPxStatusError: {exc.response.status_code} - {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)

        except httpx.RequestError as exc:
            logger.error(f"HTTPxRequestError: {str(exc)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

        except Exception as exc:
            logger.error(f"UnexpectedError: {str(exc)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    async def request_and_return(
            self,
            method: str,
            *,
            url: str,
            params: dict[str, Any] | None = None,
            data: dict[str, Any] | str | None = None,
            json: dict[str, Any] | None = None,
            files: dict[str, Any] | None = None,
            headers: dict[str, str] | None = None,
            timeout: int | None = None,
    ) -> tuple[int, dict[str, Any] | str | None, str]:
        logger.info(f"Requesting {method} {url}")
        try:
            combined_headers = {**self.headers, **(headers or {})}
            if files:
                combined_headers.pop('content-type', None)

            async with httpx.AsyncClient(timeout=timeout or self.timeout) as client:
                response = await client.request(
                    method=method.upper(),
                    url=url,
                    params=params,
                    data=None if files else data,
                    json=None if files else json,
                    files=files,
                    headers=combined_headers,
                )
                response.raise_for_status()

                try:
                    resp_data = response.json()
                except ValueError:
                    resp_data = response.text

                return response.status_code, resp_data, ""

        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            logger.error(f"HTTPxStatusError: {code} - {exc.response.text}")
            try:
                err = exc.response.json()
            except ValueError:
                err = exc.response.text
            return code, err, f"HTTPxStatusError: {code}"

        except httpx.RequestError as exc:
            logger.error(f"HTTPxRequestError: {str(exc)}")
            return 500, None, f"HTTPxRequestError: {exc}"

        except Exception as exc:
            logger.error(f"UnexpectedError: {str(exc)}")
            return 500, None, f"UnexpectedError: {exc}"

    async def get(self, url: str, params: dict[str, Any] | None = None,
                  headers: dict[str, str] | None = None) -> Any:
        resp = await self._request("GET", url, params=params, headers=headers)
        return resp.json()

    async def post(self, url: str, json: dict[str, Any] | None = None,
                   data: dict[str, Any] | str | None = None,
                   files: dict[str, Any] | None = None,
                   headers: dict[str, str] | None = None) -> Any:
        resp = await self._request("POST", url, json=json, data=data, files=files, headers=headers)
        return resp.json()

    async def put(self, url: str, json: dict[str, Any] | None = None,
                  data: dict[str, Any] | str | None = None,
                  files: dict[str, Any] | None = None,
                  headers: dict[str, str] | None = None) -> Any:
        resp = await self._request("PUT", url, json=json, data=data, files=files, headers=headers)
        return resp.json()

    async def delete(self, url: str, json: dict[str, Any] | None = None,
                     headers: dict[str, str] | None = None) -> Any:
        resp = await self._request("DELETE", url, json=json, headers=headers)
        return resp.json()

    async def download_bytes(
            self,
            url: str,
            *,
            params: dict[str, Any] | None = None,
            headers: dict[str, str] | None = None,
            timeout: int | None = None,
    ) -> tuple[bytes, str, str]:
        """
        下载 URL 指向的二进制内容，返回 (bytes, file_name, content_type)。
        :param url: 完整资源 URL
        :param params: 查询参数
        :param headers: 请求头
        :param timeout: 超时时间（秒）
        """

        download_start = time.perf_counter()
        # 走原来的 _request 拿到完整 response
        resp = await self._request(
            method="GET",
            url=url,
            params=params,
            headers=headers,
            timeout=timeout,
        )
        logger.info(f"download {url} cost={time.perf_counter() - download_start:.2f}s")
        # 2. 从 URL 解析文件名
        parsed = urlparse(url)
        file_name = os.path.basename(parsed.path) or "download"

        # 3. 优先从 Content-Type 头取
        content_type = resp.headers.get("content-type")
        if not content_type:
            # 再根据后缀猜一次
            ct, _ = mimetypes.guess_type(file_name)
            content_type = ct or "application/octet-stream"

        return resp.content, file_name, content_type


httpx_cli = HTTPXClient()
