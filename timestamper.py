
class Timestamper:
    """
    deterministik, her cagirda artan timestamp
    testler için safe (flaky olmayan) timestampler sağlar
    ts() -> 1, sonra 2, sonra 3, ... 
    """



    def __init__(self, start: int = 1) -> None: #init yapıcı-kurucu
        self._next = start #next variable 



    def __call__(self) -> int: #nesneyi fonksiyon gibi call
        v = self._next #sıradaki deger
        self._next += 1 
        return v
    

    def peek(self) -> int:  #bir sonraki verilecek deger
        return self._next #durumu degistirmeden sırada ne var kontrolu
    

    def bump_to(self, at_least: int) -> None: #sayac degerini en az at_least + 1 olacak şekilde ileri sarar
        if self._next <= at_least:  #bump_to gerş gitmeyen saat 
            self._next = at_least + 1  #gordugun en buyuk zamandan daha buyuk uret 


#tek is parcacikli / thread/safe hali de yapılabilir, 