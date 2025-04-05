from contextvars import ContextVar

from fastapi import HTTPException, Request

trace_id_context_var: ContextVar[str] = ContextVar("trace_id", default="unknown")


def get_user_data(request: Request) -> dict:
    return request.state.user_data


def get_user_id(request: Request) -> int:
    """
    从请求中获取用户ID
    :param request:
    :return:
    """
    user_data = get_user_data(request)
    user_id = user_data.get("id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="user_id is None")
    return user_id


def get_trace_id(request: Request):
    """异步任务使用"""
    trace_id = request.state.trace_id
    if trace_id is None:
        raise HTTPException(400, detail="trace_id is None")
    return trace_id


def set_trace_id_context_var(trace_id: str):
    """设置 trace_id"""
    trace_id_context_var.set(trace_id)


def get_trace_id_context_var() -> str:
    """获取 trace_id，如果未设置，则返回 None"""
    try:
        trace_id = trace_id_context_var.get()
    except LookupError:
        raise

    if trace_id == "unknown":
        raise LookupError("trace_id is unknown")

    return trace_id
