import re
from typing import Union
from datetime import datetime
from ast import literal_eval

from dateutil.parser import parse, ParserError
from pyparsing import Word, alphanums, nestedExpr
from pyparsing.exceptions import ParseException

from django.db.models import Q


WORD = Word(alphanums + " " + "-")
AND = "AND"
OR = "OR"


class ParserSearch:
    _PARSER = nestedExpr(opener='(', closer=')', content=WORD)

    @staticmethod
    def _parse_value(text_value: str) -> Union[str, int, bool, datetime]:
        '''
        Parse string value
        '''
        # parse digit
        text_value = text_value.strip()
        if text_value.isdigit():
            return int(text_value)

        # parse datetime format
        try:
            return parse(text_value)
        except ParserError:
            pass

        # parse other format
        try:
            return literal_eval(text_value)
        except ValueError:
            return text_value

    @staticmethod
    def _clean_query_string(query_string: str):
        return re.split(r'(AND|OR)', query_string)

    @classmethod
    def _make_query(cls, allowed_fields: Union[list[str], tuple[str]], query_string: str):
        query = re.match(
            r'(?P<field>[A-Za-z-0-9_]+) (?P<op>ne|eq|gt|lt) (?P<value>[\w\W]+)',
            query_string).groupdict()

        if query["field"] not in allowed_fields:
            return

        op = query["op"]
        field = "%s" % (query["field"] + "__" + op) if op not in ["eq", "ne"] else query["field"]
        qobj = Q(**{field: cls._parse_value(query["value"])})
        return ~qobj if op == "ne" else qobj

    @classmethod
    def _build_query(cls, allowed_fields: Union[list[str], tuple[str]], raw_data):
        qobj = Q()
        last_op = AND
        idx = 0

        while raw_data:
            item = raw_data[idx]
            idx += 1

            if isinstance(item, list):
                item = cls._build_query(allowed_fields, item)

            if isinstance(item, str):
                item = item.strip()

                if item.upper() in [AND, OR]:
                    last_op = item.upper()
                    item = ""

                cleaned_query = cls._clean_query_string(item)
                if len(cleaned_query) > 1:
                    raw_data[idx-1: idx] = cleaned_query
                    item = cleaned_query[0]

                if item:
                    item = cls._make_query(allowed_fields, item)

            if isinstance(item, Q):
                if last_op == AND:
                    qobj = qobj & item
                elif last_op == OR:
                    qobj = qobj | item

            if idx >= len(raw_data):
                break

        return qobj

    @staticmethod
    def _validate_parse_input(allowed_fields: Union[list[str], tuple[str]], search_phrase: str):
        if not isinstance(allowed_fields, (list, tuple)):
            raise ValueError

        if not isinstance(search_phrase, str):
            raise ValueError

    @classmethod
    def parse(cls, allowed_fields: Union[list[str], tuple[str]], search_phrase: str):
        '''
        Parse text string to Q object
        :param Union[list, tuple, None] allowed_fields, if None then return all field in search_phrase
        ex: ["model_field_name", "model_field_name"] or None

        :param str search_phrase
        ex:
        - "(date eq 2016-05-01) AND ((distance gt 20) OR (distance lt 10))"
        - "(date gt 2000-01-01) AND (distance gt 2000) OR (name eq Mars) OR (name ne Saturnus)"
        - "((date eq 2016-05-01) AND (name eq Mars)) AND ((distance gt 20) OR (distance lt 10)) AND (distance lt 10000)"
        - "date ne 2016-05-01 AND (distance gt 20 OR distance lt 10) AND active eq True"
        - "date ne 2016-05-01 AND (distance gt 20 OR distance lt 10)"
        - "date gt 2000-01-01"
        - "date gt 2000-01-01 AND distance gt 2000 OR name eq Mars OR name ne Saturnus"
        - (date ne 2016-05-01) AND (((distance gt 20) OR (distance lt 10)) AND (name eq momon))
        - (date ne 2016-05-01) AND ((((distance gt 20) OR (distance lt 10)) AND (name eq momon)) AND (date gt 2000-01-01)) OR (name ne Neptunus)"  # noqa: E501
        '''
        cls._validate_parse_input(allowed_fields, search_phrase)
        try:
            raw_data = cls._PARSER.parseString(f"({search_phrase})", parseAll=True).as_list()
            return cls._build_query(allowed_fields, raw_data)
        except (ParseException, AttributeError):
            return Q()
