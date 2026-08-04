"""R 统一返回体：err() 构造业务错误（Batch 77 补测，修复 P0-01）。"""

from app.schemas.common import R


def test_r_err_defaults():
    r = R.err()
    assert r.code == 1
    assert r.msg == "error"
    assert r.data is None


def test_r_err_custom():
    r = R.err(code=404, msg="用例不存在")
    assert r.code == 404
    assert r.msg == "用例不存在"
    assert r.data is None


def test_r_err_is_valid_response_shape():
    # 与 R.ok 同构，满足前端 envelope 约定 {code, msg, data}
    ok = R.ok(data={"id": 1})
    err = R.err(code=404, msg="not found")
    assert set(err.model_dump().keys()) == set(ok.model_dump().keys())
