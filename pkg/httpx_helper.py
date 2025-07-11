import mimetypes
import os
import time
from collections.abc import AsyncGenerator
from typing import Any
from urllib.parse import urlparse

import httpx

from pkg import orjson_dumps
from pkg.exception import AppIgnoreException
from pkg.logger_helper import logger


class HTTPXClient:
    """
    基于 httpx 封装的工具类，GET/POST/PUT/DELETE 均接收完整 URL，
    自动处理 JSON、form-data、文件上传，以及错误转换为 HTTPException。
    """

    def __init__(self, timeout: int = 60, headers: dict[str, str] | None = None):
        """
        :param timeout: 请求超时时间，默认 10 秒
        :param headers: 公共请求头，默认 {'content-type': 'application/json'}
        """
        self.timeout = timeout
        self.headers = headers or {'content-type': 'application/json'}

    async def _stream(
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
            chunk_size: int = 1024
    ) -> AsyncGenerator[bytes, None]:
        url = url.strip()
        logger.info(f"Stream Requesting: method={method}, url={url}")
        combined_headers = {**self.headers, **(headers or {})}
        if files:
            combined_headers.pop('content-type', None)

        try:
            async with httpx.AsyncClient(timeout=timeout or self.timeout) as client:
                async with client.stream(
                        method=method.upper(),
                        url=url,
                        params=params,
                        data=None if files else data,
                        json=None if files else json,
                        files=files,
                        headers=combined_headers,
                ) as response:
                    response.raise_for_status()
                    logger.info(f"Stream Response: success, status_code={response.status_code}")
                    async for chunk in response.aiter_bytes(chunk_size):
                        yield chunk
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            try:
                err_bytes = await response.aread()
                err_text = err_bytes.decode(errors="ignore")
                logger.error(f"HTTPStatusError, status_code={status_code}, err={err_text}")
            except Exception as e:
                logger.error(f"HTTPStatusError, content read failed: {e}")

            raise AppIgnoreException()
        except httpx.RequestError as exc:
            logger.error(f"HTTPxRequestError, err={exc}")
            raise AppIgnoreException() from exc
        except Exception as exc:
            logger.error(f"UnexpectedError, err={exc}")
            raise AppIgnoreException()

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
            to_raise: bool = True,
    ) -> httpx.Response | (int | None, dict[str, Any] | str | None, str):
        """
        :param method: HTTP 方法
        :param url: 完整 URL
        :param params: 查询参数
        :param data: form-data 或普通 body
        :param json: JSON body
        :param files: 文件上传 dict
        :param headers: 单次请求头
        :param timeout: 单次请求超时
        :return: httpx.Response
        """
        url = url.strip()
        logger.info(f"Requesting: method={method}, url={url}, json={json}")

        combined_headers = {**self.headers, **(headers or {})}
        if files:
            combined_headers.pop('content-type', None)

        try:
            async with httpx.AsyncClient(timeout=timeout or self.timeout) as client:
                response: httpx.Response = await client.request(
                    method=method.upper(),
                    url=url,
                    params=params,
                    data=None if files else data,
                    json=None if files else json,
                    files=files,
                    headers=combined_headers,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            try:
                resp_content = exc.response.json()
                resp_content = str(orjson_dumps(resp_content))
            except Exception as e:
                logger.error(f"parse exc.response.json() failed, err={e}")
                resp_content = exc.response.text

            logger.error(
                f"HTTPxStatusError, status_code={status_code}, err={exc}, response={resp_content}"
            )

            if to_raise:
                raise AppIgnoreException() from exc

            return None, None, resp_content
        except httpx.RequestError as exc:
            logger.error(f"HTTPxRequestError, err={exc}")

            if to_raise:
                raise AppIgnoreException() from exc

            return None, None, str(exc)
        except Exception as exc:
            logger.error(f"UnexpectedError, err={exc}")

            if to_raise:
                raise AppIgnoreException() from exc

            return None, None, str(exc)

    async def get(self,
                  url: str,
                  *,
                  params: dict[str, Any] | None = None,
                  headers: dict[str, str] | None = None,
                  timeout: int | None = None,
                  ) -> Any:
        resp: httpx.Response = await self._request("GET", url, params=params, headers=headers, timeout=timeout)
        return resp.json()

    async def post(
            self,
            url: str,
            *,
            json: dict[str, Any] | None = None,
            data: dict[str, Any] | str | None = None,
            files: dict[str, Any] | None = None,
            headers: dict[str, str] | None = None,
            timeout: int | None = None
    ) -> Any:
        resp: httpx.Response = await self._request(
            "POST", url, json=json, data=data, files=files, headers=headers, timeout=timeout
        )
        return resp.json()

    async def put(self,
                  url: str,
                  *,
                  json: dict[str, Any] | None = None,
                  data: dict[str, Any] | str | None = None,
                  files: dict[str, Any] | None = None,
                  headers: dict[str, str] | None = None,
                  timeout: int | None = None) -> Any:
        resp: httpx.Response = await self._request(
            "PUT", url, json=json, data=data, files=files, headers=headers, timeout=timeout
        )
        return resp.json()

    async def delete(self,
                     url: str,
                     *,
                     json: dict[str, Any] | None = None,
                     headers: dict[str, str] | None = None,
                     timeout: int | None = None) -> Any:
        resp: httpx.Response = await self._request("DELETE", url, json=json, headers=headers, timeout=timeout)
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

    async def stream_get(
            self,
            url: str,
            *,
            params: dict[str, Any] | None = None,
            headers: dict[str, str] | None = None,
            timeout: int | None = None,
            chunk_size: int = 1024,
    ) -> AsyncGenerator[bytes, None]:
        """
        流式GET请求
        """
        async for chunk in self._stream(
                "GET",
                url=url,
                params=params,
                headers=headers,
                timeout=timeout,
                chunk_size=chunk_size,
        ):
            yield chunk

    async def stream_post(
            self,
            url: str,
            *,
            json: dict[str, Any] | None = None,
            headers: dict[str, str] | None = None,
            timeout: int | None = None,
            chunk_size: int = 1024,
    ) -> AsyncGenerator[bytes, None]:
        """
        流式POST请求
        """
        async for chunk in self._stream(
                "POST",
                url=url,
                json=json,
                headers=headers,
                timeout=timeout,
                chunk_size=chunk_size,
        ):
            yield chunk


httpx_cli = HTTPXClient()
