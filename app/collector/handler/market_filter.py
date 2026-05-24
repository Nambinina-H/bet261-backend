"""Marches 'coeur' captures par defaut (suffisants pour les strategies, volume maitrise).
   --all-markets / settings.all_markets ignore ce filtre."""

CORE_BET_TYPE_IDS = {
    30083,  # 1X2
    30084,  # Mi-temps 1X2
    30085,  # Double Chance
    30087,  # +/- (Over/Under, toutes lignes)
    30089,  # HT/FT
    30090,  # Total de buts
    30081,  # Score exact
}
CORE_MARKET_NAMES = {"G/NG", "1X2", "Double Chance", "+/-", "HT/FT",
                     "Total de buts", "Score exact", "Mi-tps 1X2"}


def is_core_market(bet_type_id, market_name) -> bool:
    return bet_type_id in CORE_BET_TYPE_IDS or market_name in CORE_MARKET_NAMES
