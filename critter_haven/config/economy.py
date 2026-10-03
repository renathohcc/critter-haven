"""Regras econômicas provisórias — o ouro/s por criatura (creatures.json)
foi rebalanceado na Fase 10 e já não segue os valores do GDD; a taxa de
produção de itens e o preço de venda também ficam aqui. Decisão registrada em
conversa com o dev: item a cada N segundos por raridade, preço = ouro/s da
criatura x fator. Valores aqui são fáceis de rebalancear (Fase 8)."""

ITEM_INTERVAL_BY_RARITY = {
    "common": 24,
    "rare": 20,
    "special": 16,
}

ITEM_SELL_PRICE_FACTOR = 6.0

BASE_CHEST_CAPACITY = 50
