from enum import Enum


class Status(Enum):
    OK = 'green'
    NotOK = 'red'
    ExchangeClosed = 'grey'
