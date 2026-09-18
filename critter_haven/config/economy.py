"""Regras econômicas provisórias — o GDD define ouro/s por criatura, mas não
a taxa de produção de itens nem o preço de venda. Decisão registrada em
conversa com o dev: item a cada N segundos por raridade, preço = ouro/s da
criatura x fator. Valores aqui são fáceis de rebalancear (Fase 8)."""

ITEM_INTERVAL_BY_RARITY = {
    "common": 8.0,
    "rare": 5.0,
    "special": 3.0,
}

ITEM_SELL_PRICE_FACTOR = 0.5

BASE_CHEST_CAPACITY = 50
