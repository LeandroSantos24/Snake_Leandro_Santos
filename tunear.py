import itertools, strategy, simulador

def probar(partidas=60, rival=simulador.rival_gloton):
    g=e=m=0; total=0
    for i in range(partidas):
        j = simulador.Juego(semilla=i)
        a,b = j.jugar(strategy.choose_direction, rival)
        total += a.score
        if not a.viva: m+=1
        if a.score>b.score: g+=1
        elif a.score==b.score: e+=1
    return g, m, total/partidas

mejores=[]
for comida, libertad, margen, riesgo in itertools.product([6,12,20],[4,10],[2,5],[30,80]):
    strategy.PESO_COMIDA=comida; strategy.PESO_LIBERTAD=libertad
    strategy.MARGEN_SEGURIDAD=margen; strategy.PESO_RIESGO=riesgo
    g,m,s = probar()
    mejores.append((m, -g, -s, (comida,libertad,margen,riesgo)))
    print(f"comida={comida:<3} lib={libertad:<3} margen={margen} riesgo={riesgo:<3} -> muertes={m:<3} ganadas={g:<3} score={s:.0f}")
mejores.sort()
print("\nTOP 5 (menos muertes, mas victorias):")
for x in mejores[:5]: print(x)
