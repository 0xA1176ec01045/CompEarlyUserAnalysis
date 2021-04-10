import web3
import pandas as pd
from pycoingecko import CoinGeckoAPI

cg = CoinGeckoAPI()

# Compute "token weights" for each token
# for a rough estimate of capital-weighted
# early usage of the Compound protocol

# A token's capital weight is taken as the
# simple average of its USD price at CompV1deployBlock
# and its USD price at COMPlaunchBlock,
# the start and end of the early user analysis window.

# The following simplifications are adopted to
# sidestep limitations in CoinGecko historical data:
# --> Stablecoin weights are directly set to 1 
# --> Bitcoin data is used for the WBTC price
# --> Ethereum data is used for the WETH price

CompV1deployBlockDate = '26-09-2018'
COMPlaunchBlockDate   = '15-06-2020'
token_weights = {
    'sai' : 1.0, 'usdc' : 1.0, 'dai' : 1.0
}
for token in ['0x','basic-attention-token','augur','ethereum','bitcoin']:
    rawdata = cg.get_coin_history_by_id(token,CompV1deployBlockDate)
    print(rawdata)
    StartPrice = rawdata["market_data"]["current_price"]["usd"]
    print(token + CompV1deployBlockDate + str(StartPrice))
    rawdata = cg.get_coin_history_by_id(token,COMPlaunchBlockDate)
    EndPrice = rawdata["market_data"]["current_price"]["usd"]
    print(token + CompV1deployBlockDate + str(EndPrice))
    token_weights[token] = (0.5*(StartPrice+EndPrice))
print("token_weights:")
print(token_weights)
 
