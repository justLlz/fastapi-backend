class AppHTTPException(Exception):
    def __init__(self, status_code: int, detail: str = "", headers: dict | None = None):
        """
        自定义 HTTP 异常，支持任意状态码，不受 http.HTTPStatus 限制。

        :param status_code: HTTP 状态码，可以是标准或非标准
        :param detail: 详细信息，可以是字符串或字典
        :param headers: 可选的 HTTP 头
        """
        self.status_code = status_code
        self.detail = detail
        self.headers = headers
