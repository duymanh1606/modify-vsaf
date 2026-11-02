# -*- coding: utf-8 -*-
"""
test_drawio_erd — TDD test cho che do `collapsed` cua erd() trong drawio_lib.py.

Cau truc entities THAT (doc tu drawio_lib.py dong 153-183, KHONG phai
gia dinh trong task-3-brief.md):

    entities: dict name -> (domain, [ (field, type, key, note), ... ])
              # key in {'PK','FK','UK',''}; note optional (tuple co the dai 3 hoac 4)

Brief goc gia dinh entities la dict name -> list[(name,type,note)] (tuple 3 phan,
PK/FK nam trong note). Thuc te erd() dung tuple (domain, fields) o cap entity,
va field la tuple 4 phan (field,type,key,note) voi key rieng bet PK/FK/UK.
Fixture ben duoi da dieu chinh cho khop cau truc that.

Fallback: khong co pytest trong moi truong nay (khong co mang de pip install),
nen dung plain assert + __main__ runner thay vi pytest.
"""
import drawio_lib as d

ENTS = {
    "RECONCILE_BANK_SERVICE": ("core", [
        ("_id", "string", "PK", ""),
        ("general_bank_request_id", "string", "FK", ""),
        ("bank_amount", "double", "", ""),
        ("note", "string", "", ""),
    ])
}
RELS = []


def test_collapsed_hides_plain_fields():
    xml = d.erd(ENTS, RELS, collapsed=True)
    assert "_id" in xml and "general_bank_request_id" in xml
    assert "bank_amount" not in xml and "note" not in xml


def test_default_shows_all_fields():
    xml = d.erd(ENTS, RELS)
    assert "bank_amount" in xml and "note" in xml


if __name__ == "__main__":
    tests = [
        ("test_collapsed_hides_plain_fields", test_collapsed_hides_plain_fields),
        ("test_default_shows_all_fields", test_default_shows_all_fields),
    ]
    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
        except Exception as e:
            failed += 1
            print("FAIL: %s -> %r" % (name, e))
        else:
            passed += 1
            print("PASS: %s" % name)
    print("\n%d passed, %d failed" % (passed, failed))
    if failed:
        raise SystemExit(1)
