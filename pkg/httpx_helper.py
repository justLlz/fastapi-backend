from typing import Any, Tuple

import httpx
from fastapi import HTTPException, status
from loguru import logger


class HTTPXClient:
    """
    HTTP Client 基于 httpx 封装的工具类，支持 GET, POST, PUT, DELETE 请求。
    """

    def __init__(self, base_url: str, timeout: int = 10, headers: dict[str, str] | None = None):
        """
        初始化 HTTP Client
        :param base_url: API 基础 URL
        :param timeout: 请求超时时间，默认 10 秒
        :param headers: 公共请求头，默认无
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.headers = headers or {'content-type': 'application/json'}

    async def _request(
            self,
            method: str,
            endpoint: str,
            params: dict[str, Any] | None = None,
            data: dict[str, Any] | str | None = None,
            json: dict[str, Any] | None = None,
            headers: dict[str, str] | None = None,
            timeout: int | None = None,
    ) -> httpx.Response:
        """
        统一的请求方法
        :param method: 请求方法 (GET, POST, PUT, DELETE)
        :param endpoint: 接口路径
        :param params: 查询参数
        :param data: 表单数据
        :param json: JSON 数据
        :param headers: 请求头
        :param timeout: 超时时间
        :return: httpx.Response
        """
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=timeout or self.timeout) as client:
                response = await client.request(
                    method=method.upper(),
                    url=endpoint.lstrip('/'),
                    params=params,
                    data=data,
                    json=json,
                    headers={**self.headers, **(headers or {})},
                )
                response.raise_for_status()
                return response
        except httpx.HTTPStatusError as exc:
            # 处理 HTTP 错误状态码（如 4xx，5xx）
            logger.error(f"HTTPxStatusError: {exc.response.status_code} - {exc.response.text}")
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text)
        except httpx.RequestError as e:
            logger.error(f"HTTPxRequestError: {repr(e)}")
            # 处理请求错误，例如网络问题
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
        except Exception as exc:
            # 处理其他未预料到的异常
            logger.error(f"UnexpectedError: {repr(exc)}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))

    async def request_and_return(
            self,
            method: str,
            endpoint: str,
            params: dict[str, Any] | None = None,
            data: dict[str, Any] | str | None = None,
            json: dict[str, Any] | None = None,
            headers: dict[str, str] | None = None,
            timeout: int | None = None,
    ) -> Tuple[int, dict[str, Any] | str | None, str | None]:
        """
        统一的请求方法
        :param method: 请求方法 (GET, POST, PUT, DELETE)
        :param endpoint: 接口路径
        :param params: 查询参数
        :param data: 表单数据
        :param json: JSON 数据
        :param headers: 请求头
        :param timeout: 超时时间
        :return: 元组 (status_code, response_data, error_message)
        """
        logger.info(f"Requesting {method} {endpoint}")
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=timeout or self.timeout) as client:
                response = await client.request(
                    method=method.upper(),
                    url=endpoint.lstrip('/'),
                    params=params,
                    data=data,
                    json=json,
                    headers={**self.headers, **(headers or {})},
                )
                response.raise_for_status()

                # 尝试解析JSON响应，失败则返回原始文本
                try:
                    response_data = response.json()
                except ValueError:
                    response_data = response.text

                return response.status_code, response_data, None
        except httpx.HTTPStatusError as exc:
            # 处理 HTTP 错误状态码（如 4xx，5xx）
            status_code = exc.response.status_code
            logger.error(f"HTTPxStatusError: {status_code} - {exc.response.text}")

            try:
                error_data = exc.response.json()
            except ValueError:
                error_data = exc.response.text

            return exc.response.status_code, error_data, f"HTTPxStatusError: {status_code}"

        except httpx.RequestError as exc:
            # 处理请求错误（网络问题、连接超时等）
            logger.error(f"HTTPxRequestError: {repr(exc)}")
            return 500, None, f"HTTPxStatusError： {exc}"

        except Exception as exc:
            # 处理其他未预料到的异常
            logger.error(f"UnexpectedError: {repr(exc)}")
            return 500, None, f"UnexpectedError: {exc}"

    async def get(self, endpoint: str, params: dict[str, Any] | None = None,
                  headers: dict[str, str] | None = None) -> Any:
        """
        GET 请求
        :param endpoint: 接口路径
        :param params: 查询参数
        :param headers: 请求头
        :return: JSON 数据
        """
        response = await self._request("GET", endpoint, params=params, headers=headers)
        return response.json()

    async def post(self, endpoint: str, json: dict[str, Any] | None = None,
                   data: dict[str, Any] | str | None = None,
                   headers: dict[str, str] | None = None) -> Any:
        """
        POST 请求
        :param endpoint: 接口路径
        :param json: JSON 数据
        :param data: 表单数据
        :param headers: 请求头
        :return: JSON 数据
        """
        response = await self._request("POST", endpoint, json=json, data=data, headers=headers)
        return response.json()

    async def put(self, endpoint: str, json: dict[str, Any] | None = None,
                  data: dict[str, Any] | str | None = None,
                  headers: dict[str, str] | None = None) -> Any:
        """
        PUT 请求
        :param endpoint: 接口路径
        :param json: JSON 数据
        :param data: 表单数据
        :param headers: 请求头
        :return: JSON 数据
        """
        response = await self._request("PUT", endpoint, json=json, data=data, headers=headers)
        return response.json()

    async def delete(self, endpoint: str, json: dict[str, Any] | None = None,
                     headers: dict[str, str] | None = None) -> Any:
        """
        DELETE 请求
        :param endpoint: 接口路径
        :param json: JSON 数据
        :param headers: 请求头
        :return: JSON 数据
        """
        response = await self._request("DELETE", endpoint, json=json, headers=headers)
        return response.json()
