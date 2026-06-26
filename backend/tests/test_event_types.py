"""单元测试: P1-T4 动态事件类型注册能力

测试场景:
1. 初始种子数据来自 EventTypes 静态枚举
2. register_event_type 幂等
3. is_registered 正确返回
4. unregister_event_type 只允许注销动态类型
5. register → is_registered → unregister → not registered
"""
import pytest
from app.services.events import EventBus, EventTypes


@pytest.fixture(autouse=True)
def reset_eventbus():
    """每个测试前重置 EventBus 注册状态"""
    # 直接重置内部注册表
    bus = EventBus()
    with bus._reg_lock:
        bus._registered_types.clear()
        bus._seed_from_event_types()
    yield


class TestDynamicEventTypeRegistration:
    """P1-T4 动态事件类型注册"""

    def test_seeded_from_event_types(self):
        """初始种子数据来自 EventTypes 静态枚举"""
        bus = EventBus()
        types = bus.list_registered_types()
        # 验证所有静态枚举都被导入
        all_static = set()
        for attr_name in dir(EventTypes):
            if attr_name.startswith("_"):
                continue
            val = getattr(EventTypes, attr_name)
            if isinstance(val, str) and "." in val:
                all_static.add(val)
        registered_types = {t["event_type"] for t in types}
        assert all_static.issubset(registered_types), (
            f"Missing static types: {all_static - registered_types}"
        )
        # 验证都是 static 源
        for t in types:
            assert t["source"] == "static", f"{t['event_type']} should be static"

    def test_register_new_type(self):
        """注册新事件类型"""
        bus = EventBus()
        result = bus.register_event_type("test.custom_event")
        assert result is True
        assert bus.is_registered("test.custom_event") is True

    def test_register_with_version(self):
        """注册新事件类型并指定版本号"""
        bus = EventBus()
        bus.register_event_type("test.v2_event", version=2)
        types = bus.list_registered_types()
        match = [t for t in types if t["event_type"] == "test.v2_event"]
        assert len(match) == 1
        assert match[0]["version"] == 2
        assert match[0]["source"] == "dynamic"

    def test_register_idempotent(self):
        """register_event_type 幂等（已存在则跳过返回 False）"""
        bus = EventBus()
        # 首次注册成功
        assert bus.register_event_type("test.dup_event") is True
        # 再次注册返回 False
        assert bus.register_event_type("test.dup_event") is False
        # 注册已有的静态类型也返回 False
        assert bus.register_event_type(EventTypes.PLAN_APPROVED) is False

    def test_is_registered(self):
        """is_registered 正确判断"""
        bus = EventBus()
        # 静态类型已注册
        assert bus.is_registered(EventTypes.PLAN_APPROVED) is True
        # 动态注册后
        bus.register_event_type("test.my_event")
        assert bus.is_registered("test.my_event") is True
        # 不存在的类型
        assert bus.is_registered("nonexistent.type") is False

    def test_unregister_dynamic_type(self):
        """注销动态注册的事件类型"""
        bus = EventBus()
        bus.register_event_type("test.temp_event")
        assert bus.is_registered("test.temp_event") is True
        # 注销成功
        result = bus.unregister_event_type("test.temp_event")
        assert result is True
        assert bus.is_registered("test.temp_event") is False

    def test_unregister_static_type_fails(self):
        """静态枚举类型不可注销"""
        bus = EventBus()
        result = bus.unregister_event_type(EventTypes.PLAN_APPROVED)
        assert result is False
        # 仍然已注册
        assert bus.is_registered(EventTypes.PLAN_APPROVED) is True

    def test_unregister_nonexistent(self):
        """注销不存在的类型返回 False"""
        bus = EventBus()
        result = bus.unregister_event_type("does.not.exist")
        assert result is False

    def test_register_then_unregister_flow(self):
        """完整流程: register → is_registered → unregister → not registered"""
        bus = EventBus()
        new_type = "test.flow_type"

        # 注册前不存在
        assert bus.is_registered(new_type) is False

        # 注册
        assert bus.register_event_type(new_type) is True
        assert bus.is_registered(new_type) is True

        # list 中包含
        types = bus.list_registered_types()
        assert any(t["event_type"] == new_type for t in types)

        # 注销
        assert bus.unregister_event_type(new_type) is True
        assert bus.is_registered(new_type) is False

        # list 中不再包含
        types = bus.list_registered_types()
        assert not any(t["event_type"] == new_type for t in types)

    def test_list_registered_types_format(self):
        """list_registered_types 返回格式正确"""
        bus = EventBus()
        types = bus.list_registered_types()
        assert isinstance(types, list)
        for t in types:
            assert "event_type" in t
            assert "version" in t
            assert "source" in t
            assert isinstance(t["version"], int)
            assert t["source"] in ("static", "dynamic")

    def test_invalid_event_type_raises(self):
        """无效参数抛出 ValueError"""
        bus = EventBus()
        with pytest.raises(ValueError, match="non-empty"):
            bus.register_event_type("")
        with pytest.raises(ValueError, match="non-empty"):
            bus.register_event_type("   ")
        with pytest.raises(ValueError, match="positive integer"):
            bus.register_event_type("test.bad_version", version=0)
        with pytest.raises(ValueError, match="positive integer"):
            bus.register_event_type("test.bad_version", version=-1)
