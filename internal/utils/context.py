from fastapi import HTTPException, Request


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
