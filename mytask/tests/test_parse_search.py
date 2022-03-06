from datetime import datetime

from django.db.models import Q
from django.test import TestCase

from ..parser import ParserSearch
from ..models import Planet


class AnimalTestCase(TestCase):

    fixtures = ['planets.json']

    def test_positive(self):
        # Specified all search field on allowed_fields
        search = "(date ne 2016-05-01) AND ((distance gt 20) OR (distance lt 10))"
        assert ParserSearch.parse(["date", "distance"], search) == \
            ~Q(date=datetime(2016, 5, 1)) & (Q(distance__gt=20) | Q(distance__lt=10))

        search = "date ne 2016-05-01 AND (distance gt 20 OR distance lt 10)"
        assert ParserSearch.parse(["date", "distance"], search) == \
            ~Q(date=datetime(2016, 5, 1)) & (Q(distance__gt=20) | Q(distance__lt=10))

        search = "(date ne 2016-05-01) AND ((distance gt 20) OR (distance lt 10)) AND (active eq True)"
        assert ParserSearch.parse(["date", "distance", "active"], search) == \
            ~Q(date=datetime(2016, 5, 1)) & (Q(distance__gt=20) | Q(distance__lt=10)) & Q(active=True)

        search = "date ne 2016-05-01 AND (distance gt 20 OR distance lt 10) AND active eq True"
        assert ParserSearch.parse(["date", "distance", "active"], search) == \
            ~Q(date=datetime(2016, 5, 1)) & (Q(distance__gt=20) | Q(distance__lt=10)) & Q(active=True)

        search = "(date ne 2016-05-01) AND ((distance gt 20) OR (distance lt 10)) AND (active eq false)"
        assert ParserSearch.parse(["date", "distance", "active"], search) == \
            ~Q(date=datetime(2016, 5, 1)) & (Q(distance__gt=20) | Q(distance__lt=10)) & Q(active="false")

        search = "(date eq 2016-05-01) AND ((distance gt 20) OR (distance ne 25))"
        assert ParserSearch.parse(["date", "distance"], search) == \
            Q(date=datetime(2016, 5, 1)) & (Q(distance__gt=20) | ~Q(distance=25))

        search = "((date eq 2016-05-01) AND (name eq Mars)) AND ((distance gt 20) OR (distance lt 10)) AND (distance lt 10000)"  # noqa: E501
        assert ParserSearch.parse(["date", "distance", "name"], search) ==\
            (Q(date=datetime(2016, 5, 1)) & Q(name="Mars")) & (Q(distance__gt=20) | Q(distance__lt=10)) & \
            Q(distance__lt=10000)

        search = "(date eq 2016-05-01 AND name eq Mars) AND (distance gt 20 OR distance lt 10) AND distance lt 10000"
        assert ParserSearch.parse(["date", "distance", "name"], search) ==\
            (Q(date=datetime(2016, 5, 1)) & Q(name="Mars")) & (Q(distance__gt=20) | Q(distance__lt=10)) & \
            Q(distance__lt=10000)

        search = "(date eq 2016-05-01) AND (name eq Mars) AND ((distance gt 20) OR (distance lt 10)) AND (distance lt 10000)"  # noqa: E501
        assert ParserSearch.parse(["date", "distance", "name"], search) == \
            Q(date=datetime(2016, 5, 1)) & Q(name="Mars") & (Q(distance__gt=20) | Q(distance__lt=10)) &\
            Q(distance__lt=10000)

        search = "(date ne 2016-05-01) AND (name eq Mars) AND ((distance gt 20) OR (distance lt 10)) AND (distance lt 10000)"  # noqa: E501
        assert ParserSearch.parse(["date", "distance", "name"], search) == \
            ~Q(date=datetime(2016, 5, 1)) & Q(name="Mars") & (Q(distance__gt=20) | Q(distance__lt=10)) &\
            Q(distance__lt=10000)

        search = "(date gt 2000-01-01) AND (distance gt 2000) OR (name eq Mars) OR (name ne Saturnus)"
        assert ParserSearch.parse(["date", "distance", "name"], search) == \
            Q(date__gt=datetime(2000, 1, 1)) & Q(distance__gt=2000) | Q(name="Mars") | ~Q(name="Saturnus")

        search = "date lt 2000-01-01 AND distance gt 2000 OR name eq Mars OR name ne Saturnus"
        assert ParserSearch.parse(["date", "distance", "name"], search) == \
            Q(date__lt=datetime(2000, 1, 1)) & Q(distance__gt=2000) | Q(name="Mars") | ~Q(name="Saturnus")

        search = "date gt 2000-01-01"
        assert ParserSearch.parse(["date"], search) == Q(date__gt=datetime(2000, 1, 1))

        # Exclude fields test
        search = "date gt 2000-01-01 AND distance gt 2000 OR name eq Mars OR name ne Saturnus"
        assert ParserSearch.parse(["date", "name"], search) == \
            Q(date__gt=datetime(2000, 1, 1)) | Q(name="Mars") | ~Q(name="Saturnus")

        search = "(date eq 2016-05-01) AND ((distance gt 20) OR (distance lt 10))"
        assert ParserSearch.parse(["distance"], search) == \
            Q(distance__gt=20) | Q(distance__lt=10)

        search = "((date eq 2016-05-01) AND (name eq Mars)) AND ((distance gt 20) OR (distance lt 10)) AND (distance lt 10000)"  # noqa: E501
        assert ParserSearch.parse(["distance", "name"], search) ==\
            Q(name="Mars") & (Q(distance__gt=20) | Q(distance__lt=10)) & Q(distance__lt=10000)
        assert ParserSearch.parse(["name"], search) == Q(name="Mars")

        search = "((date gt 2016-05-01) AND (name eq Mars)) AND ((distance gt 20) OR (distance lt 10) OR (name ne Pluto)) AND (date lt 2000-01-01)"  # noqa: E501
        assert ParserSearch.parse(["distance", "name"], search) ==\
            Q(name="Mars") & (Q(distance__gt=20) | Q(distance__lt=10) | ~Q(name="Pluto"))
        assert ParserSearch.parse(["date"], search) ==\
            Q(date__gt=datetime(2016, 5, 1)) & Q(date__lt=datetime(2000, 1, 1))

        search = "((date gt 2000-01-01) AND (name eq Mars)) AND ((distance gt 20) OR (distance lt 10) OR (name ne Pluto)) AND (date lt 2022-01-01)"  # noqa: E501
        assert ParserSearch.parse(["distance", "date"], search) == \
            Q(date__gt=datetime(2000, 1, 1)) & (Q(distance__gt=20) | Q(distance__lt=10)) &\
            Q(date__lt=datetime(2022, 1, 1))

    def test_negative(self):
        # try to break the parser with invalid search format
        # Parser should try to parse then return the possible Q object and should not return any traceback
        search = "(date ne 2016-05-01) AND ((distance gt 20) OR (distance lt 10)))))"
        assert ParserSearch.parse(["date", "distance"], search) == \
            ~Q(date=datetime(2016, 5, 1)) & (Q(distance__gt=20) | Q(distance__lt=10))

        search = "(date ne 2016-05-01 AND ((distance gt 20) OR (distance lt 10))"
        assert ParserSearch.parse(["date", "distance"], search) == \
            ~Q(date=datetime(2016, 5, 1)) & Q(distance__gt=20) | Q(distance__lt=10)

        search = "((date ne 2016-05-01 AND ((distance gt 20) OR (distance lt 10))"
        assert ParserSearch.parse(["date", "distance"], search) == \
            ~Q(date=datetime(2016, 5, 1)) & Q(distance__gt=20) | Q(distance__lt=10)

        search = "(((date ne 2016-05-01 AND ((distance gt 20) OR (distance lt 10))"
        assert ParserSearch.parse(["date", "distance"], search) == Q()

        search = "(date ne 2016-05-01)))) AND ((distance gt 20) OR (distance lt 10))"
        assert ParserSearch.parse(["date", "distance"], search) == Q()

        search = "(date ne 2016-05-01) AND (((((distance gt 20) OR (distance lt 10))"
        assert ParserSearch.parse(["date", "distance"], search) == Q()

        search = "(((((date ne 2016-05-01) AND (()"
        assert ParserSearch.parse(["date", "distance"], search) == Q()

        search = "OR ANY Random AND Text"
        assert ParserSearch.parse(["date", "distance"], search) == Q()

        search = ""
        assert ParserSearch.parse(["date", "distance"], search) == Q()

        search = "date nexxx 2016-05-01"
        assert ParserSearch.parse(["date"], search) == Q()

        search = "(date eq 2016-05-01) AND (((name eq Mars) AND (distance gt 20)) OR (distance lt 10)) AND (distance lt 10000)"  # noqa: E501
        assert ParserSearch.parse(["date", "distance"], search) == Q()

        # Test with invalid and unspecified allowed field
        search = "(date ne 2016-05-01) AND ((distance gt 20) OR (distance lt 10))"
        assert ParserSearch.parse(["field", "any"], search) == Q()

        search = "(date ne 2016-05-01) AND ((distance gt 20) OR (distance lt 10))"
        assert ParserSearch.parse([], search) == Q()

        search = "(date ne 2016-05-01) AND ((distance gt 20) OR (distance lt 10))"
        try:
            ParserSearch.parse(None, search)
        except Exception as ex:
            assert isinstance(ex, ValueError)

        search = ["1", "2", "3"]
        try:
            ParserSearch.parse(["a", "b", "c"], search)
        except Exception as ex:
            assert isinstance(ex, ValueError)

    def test_to_model(self):
        '''
        Test use the parser with models and with fixtures loaded with below sample data
        sample data:
          Planet(**{"name": "Mars", "distance": 100, "date": date(2013, 10, 2), "description": "this is mars"}),
          Planet(**{"name": "Pluto", "distance": 90000, "date": date(2012, 10, 2)}),
          Planet(**{"name": "Uranus", "distance": 2500, "date": date(2011, 10, 2), "description": "this is uranus"}),
          Planet(**{"name": "Saturnus", "distance": 1700, "date": date(2020, 10, 2), "description": "OK"}),
          Planet(**{"name": "Venus", "distance": 6500, "date": date(2009, 10, 2)}),
        '''
        assert Planet.objects.all().count() == 5
        search_phrase = "(date gt 2000-01-01) AND (distance gt 2000) OR (name eq Mars) OR (name eq Saturnus)"
        query_str = ParserSearch.parse(["date", "distance", "name"], search_phrase)
        query = Q(date__gt=datetime(2000, 1, 1)) & Q(distance__gt=2000) | Q(name="Mars") | Q(name="Saturnus")

        assert query_str == query
        result_query = Planet.objects.filter(query)
        result_query_str = Planet.objects.filter(query_str)
        assert result_query.count() == result_query_str.count()

        for i in range(len(result_query_str)):
            assert result_query[i].pk == result_query_str[i].pk
