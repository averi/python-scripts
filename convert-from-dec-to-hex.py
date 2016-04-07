#!/usr/bin/python

remainders = []
remainders_hex = []
phrase = "Please enter a number you want to convert from dec to hex: "

number = raw_input(phrase)
number = int(number)


def remainders_on_a_list(number):
    while True:
        divided_by_number = number / 16
        _remainder = int(number % 16)

        if number < 16:
            remainders.append(int(_remainder))
            break

        remainders.append(_remainder)
        number = divided_by_number


def single_number_dec_to_hex(_number):
    if _number == 10:
        _number = str('A')
    elif _number == 11:
        _number = str('B')
    elif _number == 12:
        _number = str('C')
    elif _number == 13:
        _number = str('D')
    elif _number == 14:
        _number = str('E')
    elif _number == 15:
        _number = str('F')
    else:
        _number = _number

    return str(_number)


def from_dec_to_hex(_number):
    remainders_on_a_list(_number)

    for x in remainders:
        remainders_hex.append(single_number_dec_to_hex(x))

    print ''.join(remainders_hex[::-1])

from_dec_to_hex(number)
