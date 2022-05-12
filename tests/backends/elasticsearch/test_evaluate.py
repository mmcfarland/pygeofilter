from elasticsearch_dsl import (
    connections,
    Index,
    Document,
    InnerDoc,
    Nested,
    Date,
    Text,
    Float,
    Integer,
    GeoShape,
    GeoPoint,
)
import pytest

from pygeofilter.parsers.ecql import parse
from pygeofilter.util import parse_datetime
from pygeofilter import ast
from pygeofilter.backends.elasticsearch import to_filter


class RecordMeta(InnerDoc):
    float_meta_attribute = Float()
    int_meta_attribute = Integer()
    str_meta_attribute = Text()
    datetime_meta_attribute = Date()


class Record(Document):
    identifier = Text()
    geometry = GeoShape()
    center = GeoPoint()
    float_attribute = Float()
    int_attribute = Integer()
    str_attribute = Text()
    maybe_str_attribute = Text()
    datetime_attribute = Date()
    record_metas = Nested(RecordMeta)

    class Index:
        name = "record"


@pytest.fixture(scope="session")
def data():
    connections.create_connection(
        hosts=['https://user:secret@localhost:9200'],
        verify_certs=False,
    )
    # connections.create_connection(alias='my_new_connection', hosts=['localhost'], timeout=60)
    Record.init()

    record_a = Record(
        identifier="A",
        geometry="MULTIPOLYGON(((0 0, 0 5, 5 5,5 0,0 0)))",
        center="POINT(2.5 2.5)",
        float_attribute=0.0,
        int_attribute=5,
        str_attribute="this is a test",
        maybe_str_attribute=None,
        datetime_attribute=parse_datetime("2000-01-01T00:00:00Z"),
    )
    record_a.save()

    record_b = Record(
        identifier="B",
        geometry="MULTIPOLYGON(((5 5, 5 10, 10 10,10 5,5 5)))",
        center="POINT(7.5 7.5)",
        float_attribute=30.0,
        int_attribute=None,
        str_attribute="this is another test",
        maybe_str_attribute="some value",
        datetime_attribute=parse_datetime("2000-01-01T00:00:10Z"),
    )
    record_b.save()

    record_index = Index(Record.Index.name)
    record_index.refresh()

    print([
        r.int_attribute for r in Record.search().execute()])

    yield [record_a, record_b]
    record_index.delete()


def filter_(ast):
    query = to_filter(ast)
    print(query)
    breakpoint()
    result = Record.search().query(query).execute()
    print([r.identifier for r in result])
    return result


def test_comparison(data):
    result = filter_(parse('int_attribute = 5'))
    print(result)
    assert len(result) == 1 and result[0].identifier == data[0].identifier

    result = filter_(parse('float_attribute < 6'))
    assert len(result) == 1 and result[0].identifier == data[0].identifier

    result = filter_(parse('float_attribute > 6'))
    assert len(result) == 1 and result[0].identifier == data[1].identifier

    result = filter_(parse('int_attribute <= 5'))
    assert len(result) == 1 and result[0].identifier == data[0].identifier

    result = filter_(parse('float_attribute >= 8'))
    assert len(result) == 1 and result[0].identifier == data[1].identifier

    result = filter_(parse('float_attribute <> 0.0'))
    assert len(result) == 1 and result[0].identifier == data[1].identifier


def test_combination(data):
    result = filter_(parse('int_attribute = 5 AND float_attribute < 6.0'))
    assert len(result) == 1 and result[0].identifier is data[0].identifier

    result = filter_(parse('int_attribute = 6 OR float_attribute < 6.0'))
    assert len(result) == 1 and result[0].identifier is data[0].identifier


def test_between(data):
    result = filter_(parse('float_attribute BETWEEN -1 AND 1'))
    assert len(result) == 1 and result[0].identifier is data[0].identifier

    # result = filter_(parse('int_attribute NOT BETWEEN 4 AND 6'))
    # assert len(result) == 1 and result[0].identifier is data[1].identifier


def test_like(data):
    result = filter_(parse('str_attribute LIKE \'this is . test\''))
    assert len(result) == 1 and result[0] is data[0]

    result = filter_(parse('str_attribute LIKE \'this is % test\''))
    assert len(result) == 2

    result = filter_(parse('str_attribute NOT LIKE \'% another test\''))
    assert len(result) == 1 and result[0] is data[0]

    result = filter_(parse('str_attribute NOT LIKE \'this is . test\''))
    assert len(result) == 1 and result[0] is data[1]

    result = filter_(parse('str_attribute ILIKE \'THIS IS . TEST\''))
    assert len(result) == 1 and result[0] is data[0]

    result = filter_(parse('str_attribute ILIKE \'THIS IS % TEST\''))
    assert len(result) == 2


# def test_in(data):
#     result = filter_(parse('int_attr IN ( 1, 2, 3, 4, 5 )'))
#     assert len(result) == 1 and result[0] is data[0]

#     result = filter_(parse('int_attr NOT IN ( 1, 2, 3, 4, 5 )'))
#     assert len(result) == 1 and result[0] is data[1]


def test_null(data):
    result = filter_(parse('maybe_str_attribute IS NULL'))
    assert len(result) == 1 and result[0].identifier is data[0].identifier

    result = filter_(parse('maybe_str_attribute IS NOT NULL'))
    assert len(result) == 1 and result[0].identifier is data[1].identifier


# def test_has_attr():
#     result = filter_(parse('extra_attr EXISTS'))
#     assert len(result) == 1 and result[0] is data[0]

#     result = filter_(parse('extra_attr DOES-NOT-EXIST'))
#     assert len(result) == 1 and result[0] is data[1]


def test_temporal(data):
    result = filter_(
        parse('datetime_attribute BEFORE 2000-01-01T00:00:05.00Z'),
    )
    assert len(result) == 1 and result[0].identifier is data[0].identifier

    result = filter_(
        parse('datetime_attribute AFTER 2000-01-01T00:00:05.00+01:00'),
    )
    assert len(result) == 1 and result[0].identifier is data[1].identifier


# def test_array():
#     result = filter_(
#         ast.ArrayEquals(
#             ast.Attribute('array_attr'),
#             [2, 3],
#         ),
#         data
#     )
#     assert len(result) == 1 and result[0] is data[0]

#     result = filter_(
#         ast.ArrayContains(
#             ast.Attribute('array_attr'),
#             [1, 2, 3, 4],
#         ),
#         data
#     )
#     assert len(result) == 1 and result[0] is data[1]

#     result = filter_(
#         ast.ArrayContainedBy(
#             ast.Attribute('array_attr'),
#             [1, 2, 3, 4],
#         ),
#         data
#     )
#     assert len(result) == 1 and result[0] is data[0]

#     result = filter_(
#         ast.ArrayOverlaps(
#             ast.Attribute('array_attr'),
#             [5, 6, 7],
#         ),
#         data
#     )
#     assert len(result) == 1 and result[0] is data[1]


def test_spatial(data):
    result = filter_(
        parse('INTERSECTS(point_attr, ENVELOPE (0 1 0 1))'),
    )
    assert len(result) == 1 and result[0] is data[0]

    result = filter_(
        parse('EQUALS(point_attr, POINT(2 2))'),
    )
    assert len(result) == 1 and result[0] is data[1]

    result = filter_(
        parse('BBOX(point_attr, 0.5, 0.5, 1.5, 1.5)'),
    )
    assert len(result) == 1 and result[0] is data[0]


def test_arithmetic():
    result = filter_(
        parse('int_attr = float_attr - 0.5'),
        data,
    )
    assert len(result) == 2

    result = filter_(
        parse('int_attr = 5 + 20 / 2 - 10'),
        data,
    )
    assert len(result) == 1 and result[0] is data[0]


def test_function():
    result = filter_(
        parse('sin(float_attr) BETWEEN -0.75 AND -0.70'),
        data,
    )
    assert len(result) == 1 and result[0] is data[0]


def test_nested():
    result = filter_(
        parse('"nested_attr.str_attr" = \'this is a test\''),
        data,
    )
    assert len(result) == 1 and result[0] is data[0]
