# Definicja symboli (EBNF)
```
nonzero_digit = '1' | '2' | '3' | '4' | '5' | '6' | '7' | '8' | '9';
digit = '0' | nonzero_digit;
small_letter = 'a' | 'b' | 'c' | 'd' | 'e' | 'f' | 'g' | 'h' | 'i' |
    'j' | 'k' | 'l' | 'm' | 'n' | 'o' | 'p' | 'q' | 'r' | 's' | 't' |
    'u' | 'v' | 'w' | 'x' | 'y' | 'z';
capital_letter = 'A' | 'B' | 'C' | 'D' | 'E' | 'F' | 'G' | 'H' | 'I' |
    'J' | 'K' | 'L' | 'M' | 'N' | 'O' | 'P' | 'Q' | 'R' | 'S' | 'T' |
    'U' | 'V' | 'W' | 'X' | 'Y' | 'Z';
symbol = ' ' | '\' | '|' | '/' | '+' | '-' | '.' | ',' | ':';

max_two_digit_unsigned = digit | (nonzero_digit, digit);
max_three_digit_unsigned = digit | (nonzero_digit, digit, [digit]);
character = digit | small_letter | capital_letter | symbol;
nonempty_string = character, {character}
year = 4 * digit;
month = ('0', nonzero_digit) | ('1', ('0' | '1' | '2'));
day = (('0' | '1' | '2'), nonzero_digit) | ('3', ('0' | '1'));
hour = (('0' | '1'), digit) | ('2', ('0' | '1' | '2' | '3'));
minute = ('0' | '1' | '2' | '3' | '4' | '5'), digit;

date = '"', year, '-', month, '-', day, '"';
status = 'null' | '"0"' | '"1"';
czasObslugi = '"', max_three_digit_unsigned , '"';
lp = 'null' | ('"', nonzero_digit, [digit] , '"');
idGrupy = '"', nonzero_digit, 6 * [digit], '"';
liczbaCzynnychStan = max_two_digit_unsigned;
nazwaGrupy = '"', nonempty_string, '"'
literaGrupy = '"', [capital_letter], '"';
liczbaKlwKolejce = max_three_digit_unsigned;
aktualnyNumer = '"', [((capital_letter, 3 * digit) | max_three_digit_unsigned)], '"';
time = '"', hour , ':', minute , '"';
error = '"', nonempty_string, '"'
```

# Struktura odpowiedzi JSON
1. Poprawna
```json
{
    "result": {
        "date": date,
        "grupy": [{
            "status": status,
            "czasObslugi": czasObslugi,
            "lp": lp,
            "idGrupy": idGrupy,
            "liczbaCzynnychStan": liczbaCzynnychStan,
            "nazwaGrupy": nazwaGrupy,
            "literaGrupy": literaGrupy,
            "liczbaKlwKolejce": liczbaKlwKolejce,
            "aktualnyNumer": aktualnyNumer,
        },],
        "time": time
    }
}
```

2. Błąd
```json
{
    "result": "false",
    "error": error
}
```

# Budowa wewnętrznych struktur danych
1. lista zwracana przez WSStoreAPI.get_office_list()
```json
[
    {
        'name': 'nazwa urzędu',             //str
        'key': 'identyfikator-api-urzedu'   //str
    },
    ...
]
```

2. lista zwracana przez WSStoreAPI.get_matter_list()
```json
[
    {
        'name': nazwaGrupy,                  //str
        'ordinal': lp,                       //int / None
        'group_id': idGrupy                  //int
    },
    ...
]
```

3. lista zwracana przez WSStoreAPI.get_sample_list()
```
[
    {
        'queue_length': liczbaKlwKolejce,    //int
        'open_counters': liczbaCzynnychStan, //int
        'current_number': aktualnyNumer,     //str
        'time': date time                    //str
    },
    ...
]
```
