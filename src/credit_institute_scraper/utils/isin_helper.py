

def build_isin_code(country_code: str, fund_code: str) -> str:
    isin_without_check_digit = country_code + fund_code.zfill(9)
    numeric_isin_str = ""
    for char in isin_without_check_digit:
        if not char.isdigit():
            numeric_isin_str += str(ord(char) - 55)
        else:
            numeric_isin_str += char

    numeric_isin_list = list(numeric_isin_str)

    sum_of_digits = 0
    for i in range(len(numeric_isin_list)):
        number = int(numeric_isin_list[i])
        if i % 2 == 0:
            number *= 2

        for digit in str(number):
            sum_of_digits += int(digit)

    check_digit_helper = sum_of_digits
    while True:
        if check_digit_helper % 10 == 0:
            break
        else:
            check_digit_helper += 1

    check_digit = check_digit_helper - sum_of_digits

    return isin_without_check_digit + str(check_digit)


