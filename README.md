# systemy-kolejkowe

Prezentacja bieżących danych z systemów kolejkowych jednostek Urzędu m.st. Warszawy i Dzielnic.

# Funkcjonalność
- wyświetlanie listy wszystkich dostępnych urzędów
- wyświetlanie listy wszystkich rodzajów spraw możliwych do załatwienia w danym urzędzie
- wyświetlenia aktualnego stanu kolejki dla danej sprawy w urzędzie (liczba stanowisk, liczba osób w kolejce, aktualny numer)
aktywnego monitorowanie aktualnego stanu kolejki dla wybranych grup urzędowych w wybranych urzędach (dopuszczalny interfejs konsolowy, ale lepszy byłby graficzny lub webowy)
- wizualizacja monitorowanego stanu kolejki na wykresie z seriami (np. z użyciem pyplot). Oś X - czas; oś Y - liczba osób w kolejce; każda grupa urzędowa to oddzielna seria
- lokalne cache'owania pobieranych wyników (w celu ograniczenia liczby dostępów do API, pytanie o te same dane nie powinno być zadawane częściej niż co 30 sekund)