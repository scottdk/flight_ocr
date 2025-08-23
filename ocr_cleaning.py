import re

def clean_lines(lines):
    """
    Clean OCR output lines for price extraction and analysis.
    - Remove any characters before a dollar sign, replace dot with comma, replace multiple commas with just one comma.
    - Replace commonly mistaken letters with numbers after the dollar sign.
    - Returns (cleaned_lines, price_pattern)
    """
    
    # Adjust price_pattern to match "$1", "$999", "$1,000", "$999,999"
    price_pattern = re.compile(r'^\$\d{1,3}(?:,\d{3})*$')
    # price_pattern = re.compile(r'^\$\d{1,3}(,\d{3})*$')
    def fix_letters_after_dollar(line):
        if '$' in line:
            parts = line.split('$', 1)
            prefix = parts[0] + '$'
            rest = parts[1]
            rest_fixed = (
                rest.replace('S', '5')
                    .replace('s', '5')
                    .replace('O', '0')
                    .replace('o', '0')
                    .replace('I', '1')
                    .replace('l', '1')
                    .replace('B', '8')
                    .replace('Z', '2')
                    .replace('G', '6')
                    .replace('Q', '0')
            )
            return prefix + rest_fixed
        return line
      
    # Fix common OCR mistakes after the dollar sign
    lines = [fix_letters_after_dollar(line) for line in lines]
    
    # Remove any characters before a dollar sign
    lines = [re.sub(r'^.*?\$', '$', line) if '$' in line else line for line in lines]

    # Replace dots with commas
    lines = [line.replace('.', ',') for line in lines]
    
    # Remove multiple commas and ensure only one comma is used
    lines = [re.sub(r',+', ',', line) for line in lines]

    # insert commas before every block of three digits so that the line matches the price pattern
    lines = [re.sub(r'(?<=\d)(?=(\d{3})+(?!\d))', ',', line) for line in lines]

    return lines, price_pattern
