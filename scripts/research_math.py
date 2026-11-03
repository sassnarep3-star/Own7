"""Pricing identities only. No fitted model, NBA data, or invented forecasts."""
import math

def probability(p):
    if not math.isfinite(p) or not 0 <= p <= 1:
        raise ValueError('Probability must be finite and in [0, 1]')
    return p

def fair_decimal(p):
    probability(p)
    if p == 0: raise ValueError('Zero probability has no finite fair price')
    return 1 / p

def expected_net(p_win, odds, p_push=0):
    probability(p_win); probability(p_push)
    if p_win+p_push>1 or not math.isfinite(odds) or odds<=1:
        raise ValueError('Invalid settlement probabilities or decimal odds')
    return p_win*(odds-1)-(1-p_win-p_push)

def no_vig(prices):
    if len(prices)<2 or any(not math.isfinite(d) or d<=1 for d in prices):
        raise ValueError('Need at least two valid decimal prices')
    implied=[1/d for d in prices]; total=sum(implied)
    return [p/total for p in implied]

def pearson(x,y):
    if len(x)!=len(y) or len(x)<3: raise ValueError('Need at least three aligned pairs')
    if not all(math.isfinite(v) for v in [*x,*y]):raise ValueError('Nonfinite input')
    a=[v-sum(x)/len(x) for v in x];b=[v-sum(y)/len(y) for v in y]
    den=math.sqrt(sum(v*v for v in a)*sum(v*v for v in b))
    if den==0:raise ValueError('Constant series: undefined correlation')
    return sum(u*v for u,v in zip(a,b))/den
