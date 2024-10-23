
def format_in_lakhs(num):
    num_parts = "{:.2f}".format(num).split(".")
    integer_part = num_parts[0]
    fractional_part = num_parts[1]

    reversed_integer = integer_part[::-1]

    formatted_reversed = ",".join([reversed_integer[i:i+2] for i in range(3, len(reversed_integer), 2)])
    
    formatted_integer = reversed_integer[:3] + "," + formatted_reversed if len(reversed_integer) > 3 else reversed_integer
    
    formatted_number = formatted_integer[::-1] + "." + fractional_part
    return formatted_number
