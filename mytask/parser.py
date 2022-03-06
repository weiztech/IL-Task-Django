import re
from typing import Union
from datetime import datetime
from ast import literal_eval

from dateutil.parser import parse, ParserError

from django.db.models import Q


EQ = " eq "
GT = " gt "
LT = " lt "
NE = " ne "


class ParserSearch:
    PARSE_EXPR = {
        EQ: "",
        GT: "__gt",
        LT: "__lt"
    }

    REVERSE_PAR = {
        "(": ")",
        "((": "))"
    }

    @staticmethod
    def parse_value(text_value: str) -> Union[str, int, bool, datetime]:
        '''
        Parse string value
        '''
        if text_value.isdigit():
            return literal_eval(text_value)

        # parse datetime format
        try:
            return parse(text_value)
        except ParserError:
            pass

        # parse other than datetime format
        try:
            return literal_eval(text_value)
        except ValueError:
            return text_value

    @staticmethod
    def get_text(text_value: str) -> str:
        '''
        return value inside parenthesis
        ex: (date eq 2016-05-01)
        return date eq 2016-05-01
        '''
        search = re.search(r'\(([^)]+)', text_value).groups()[0]
        return search

    @classmethod
    def make_q_object(cls, allowed_fields: Union[list, tuple], text: str) -> Union[None, Q]:
        '''
        Create Q object from string, return None if expression not found
        '''
        if "(" in text and ")" in text:
            text = cls.get_text(text)

        field = text.split(" ")[0]
        if field not in allowed_fields:
            return

        for expr in [EQ, GT, LT, NE]:
            if expr in text:
                value = text.split(expr)[-1]
                field = f"{field}{cls.PARSE_EXPR[expr]}" if expr != NE else field
                qobj = Q(**{field: cls.parse_value(value)})
                if expr == NE:
                    qobj.negate()

                return qobj

    @classmethod
    def merge_value(cls, idx: int, split_text: list[str], allowed_fields: Union[list, tuple]) -> Q:
        '''
        Merge the level 2 nested parenthesis query and return Q object
        '''
        if "((" in split_text[idx]:
            end_par = cls.REVERSE_PAR["(("]
        else:
            end_par = cls.REVERSE_PAR["("]

        last_idx = idx
        stop = False
        for text in split_text[idx:]:
            if end_par in text:
                stop = True

            split_text[last_idx] = text.replace("(", "").replace(")", "").strip()
            last_idx += 1
            if stop:
                break

        value = cls.build_query(allowed_fields, split_text[idx: last_idx+1])
        split_text[idx: last_idx] = ""
        return value

    @classmethod
    def build_query(cls, allowed_fields: Union[list, tuple], split_text: list[str]) -> Q:
        query = None
        idx = 0
        while True:
            value = split_text[idx].strip()
            if value.startswith("(((") or value.endswith(")))"):
                # nested more than 2 level is not allowed and return Q
                return Q()

            if (value.startswith("((") and not value.endswith("))")) or \
                    value.startswith("(") and not value.endswith(")"):
                value = cls.merge_value(idx, split_text, allowed_fields)
                qobj = value

            if not isinstance(value, Q):
                qobj = cls.make_q_object(allowed_fields, value)

            if query is None:
                query = qobj

            if qobj and query != qobj:
                op = None if not idx else split_text[idx-1].strip()
                if op == "AND":
                    query = query & qobj
                elif op == "OR":
                    query = query | qobj

            idx += 1
            if idx >= len(split_text):
                break

        return query or Q()

    @classmethod
    def split_text(cls, text: str) -> str:
        return re.split(r'[ ]([AND, OR]+\b)', text)

    @classmethod
    def parse(cls, allowed_fields: Union[list, tuple], search_phrase: str) -> Q:
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
        '''
        try:
            if not isinstance(allowed_fields, (list, tuple)):
                raise ValueError("Allowed fields is invalid")

            if not isinstance(search_phrase, str):
                raise ValueError("search_phrase should be string")

            return cls.build_query(allowed_fields, cls.split_text(search_phrase))
        except IndexError:
            # Found Invalid format, return empty Q
            return Q()
