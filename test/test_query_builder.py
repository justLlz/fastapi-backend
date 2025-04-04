import uuid
from datetime import datetime

import pytest

from internal.dao import CountBuilder, QueryBuilder, UpdateBuilder
from internal.models.user import User


class TestQueryBuilder:
    @pytest.fixture
    async def before(self):
        test_user = User.init_by_phone("18008069974")
        test_user.username = f"lilinze_{uuid.UUID.hex}"
        test_user.account = f"lilinze_{uuid.UUID.hex}"
        await test_user.save()
        yield QueryBuilder(User), test_user
        test_user.deleted_at = datetime.now()
        await test_user.save()

    @pytest.mark.asyncio
    async def test_operators(self, before):
        """包含完整生命周期的测试"""
        # 1. 验证测试用户创建成功
        builder, test_user = before
        created_user = await builder.eq("id", test_user.id).get_or_exec()
        assert created_user.username == test_user.username
        assert created_user.account == test_user.account
        assert created_user.phone == test_user.phone

        # 2. 测试各种查询操作符
        # eq
        user = await builder.eq("id", test_user.id).get_or_none()
        assert user.id == test_user.id

        # ne
        users = await builder.ne("id", test_user.id).scalars_all()
        for user in users:
            assert user.id != test_user.id

        # gt (假设ID是递增的)
        users = await builder.gt("id", test_user.id - 1).scalars_all()
        assert any(u.id == test_user.id for u in users)

        # lt
        users = await builder.lt("id", test_user.id + 1).scalars_all()
        assert any(u.id == test_user.id for u in users)

        # ge
        users = await builder.ge("id", test_user.id).scalars_all()
        assert any(u.id == test_user.id for u in users)

        # le
        users = await builder.le("id", test_user.id).scalars_all()
        assert any(u.id == test_user.id for u in users)

        # in_
        users = await builder.in_("id", [test_user.id]).scalars_all()
        assert any(u.id == test_user.id for u in users)

        # like
        users = await builder.like("username", "%lilinze%").scalars_all()
        assert any(u.id == test_user.id for u in users)

        # is_null
        users = await builder.is_null("deleted_at").scalars_all()
        assert any(u.id == test_user.id for u in users)

        # between
        users = await builder.between("id", (test_user.id - 1, test_user.id + 1)).scalars_all()
        assert any(u.id == test_user.id for u in users)

        # 3. 测试更新操作
        await UpdateBuilder(test_user).update(username="updated_name").execute()

        # 验证更新
        updated_user = await builder.eq("id", test_user.id).get_or_exec()
        assert updated_user.username == "updated_name"

        # 4. 测试计数
        count = await CountBuilder(User).count()
        assert count >= 1  # 至少包含我们的测试用户

    @pytest.mark.asyncio
    async def test_complex_queries(self, before):
        """测试复杂查询组合"""
        # AND 条件
        builder, test_user = before
        users = await builder \
            .eq("username", test_user.username) \
            .eq("account", test_user.account) \
            .scalars_all()
        assert any(u.id == test_user.id for u in users)

        # OR 条件
        users = await builder.or_(
            User.username == test_user.username,
            User.account == "nonexistent"
        ).scalars_all()
        assert any(u.id == test_user.id for u in users)

        # BETWEEN 条件
        users = await builder.between(
            "id",
            (test_user.id - 1, test_user.id + 1)
        ).scalars_all()
        assert any(u.id == test_user.id for u in users)


if __name__ == '__main__':
    # 执行测试用例
    pytest.main(["-v", "--asyncio-mode=auto"])
