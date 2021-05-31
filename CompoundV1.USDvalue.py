import pandas as pd
import web3
import requests
import json
from datetime import date, timedelta
from time import sleep

# Replace all token balances with corresponding USD values
# via Compound's MarketHistoryService

infile  = 'CompoundV1.EarlyUserEvents.csv'
outfile = 'CompoundV1.EarlyUserPricedEvents.csv'

# Compound V1 contract metadata
CompV1 = {
  "address"     : '0x3FDA67f7583380E67ef93072294a7fAc882FD7E7',
  "deployBlock" : 6400278,
  "abi"         : 'CompoundV1.abi.json'
}
ZRX = {
  "address"     : '0xE41d2489571d322189246DaFA5ebDe1F4699F498',
  "label"       : 'ZRX',
  "decimals"    : 18
}
BAT = {
  "address"     : '0x0D8775F648430679A709E98d2b0Cb6250d2887EF',
  "label"       : 'BAT',
  "decimals"     : 18
}
REP = {
  "address"     : '0x1985365e9f78359a9B6AD760e32412f4a445E862',
  "label"       : 'REP',
  "decimals"    : 18
}
WETH = {
  "address"     : '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2',
  "label"       : 'WETH',
  "decimals"    : 18
}
SAI = {
  "address"     : '0x89d24A6b4CcB1B6fAA2625fE562bDD9a23260359',
  "label"       : 'SAI',
  "decimals"    : 18
}
V1Tokens = [ZRX,BAT,REP,WETH,SAI]

# cToken contract metadata
# Only includes contracts deployed before block 9601359 (release of COMP)
cZRX = {
  "address"     : '0xB3319f5D18Bc0D84dD1b4825Dcde5d5f7266d407',
  "deployBlock" : 7710735,
  "abi"         : 'cZRX.abi.json'
}
cBAT = {
  "address"     : '0x6C8c6b02E7b2BE14d4fA6022Dfd6d75921D90E4E',
  "deployBlock" : 7710735,
  "abi"         : 'cBAT.abi.json'
}
cSAI = {
  "address"     : '0xF5DCe57282A584D2746FaF1593d3121Fcac444dC',
  "deployBlock" : 7710752,
  "abi"         : 'cSAI.abi.json'
}
cREP = {
  "address"     : '0x158079Ee67Fce2f58472A96584A73C7Ab9AC95c1',
  "deployBlock" : 7710755,
  "abi"         : 'cREP.abi.json',
}
cETH = {
  "address"     : '0x4Ddc2D193948926D02f9B1fE9e1daa0718270ED5',
  "deployBlock" : 7710758,
  "abi"         : 'cETH.abi.json',
}
cUSDC = {
  "address"     : '0x39AA39c021dfbaE8faC545936693aC917d5E7563',
  "deployBlock" : 7710760,
  "abi"         : 'cUSDC.abi.json',
}
cWBTC = {
  "address"     : '0xC11b1268C1A384e55C48c2391d8d480264A3A7F4',
  "deployBlock" : 8163813,
  "abi"         : 'cWBTC.abi.json'
}
cDAI = {
  "address"     : '0x5d3a536E4D6DbD6114cc1Ead35777bAB948E3643',
  "deployBlock" : 8983575,
  "abi"         : 'cDAI.abi.json'
}
cTokens = [cZRX,cBAT,cSAI,cREP,cETH,cUSDC,cWBTC,cDAI]
tokenList = ['ZRX','BAT','REP','WETH','SAI','ETH','USDC','WBTC','DAI']

# Finally we also need decimals of the underlying tokens that weren't in V1
USDC = {
  "address"     : '0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48',
  "decimals"    : 6
}
WBTC = {
  "address"     : '0x2260fac5e5542a773aa44fbcfedf7c193bc2c599',
  "decimals"    : 8
}
DAI = {
  "address"     : '0x6b175474e89094c44da98b954eedeac495271d0f',
  "decimals"    : 18
}
ETH = {
  "decimals"    : 18
}
CoinGeckoLabel = {'ZRX' : '0x',
                  'BAT' : 'basic-attention-token',
                  'REP' : 'augur',
                  'WETH': 'ethereum', # use ethereum records for WETH price (CoinGecko weth has holes)
                  'SAI' : 'sai',
                  'ETH' : 'ethereum',
                  'USDC': 'usd-coin',
                  'WBTC': 'wrapped-bitcoin',
                  'DAI' : 'dai'
                 }

CompV1deployBlock      = 6400278
EarlyUserCutoffBlock   = 9555731

# Get a web3 object pulling data from Infura Ethereum Mainnet RPC
w3 = web3.Web3(web3.Web3.HTTPProvider('https://mainnet.infura.io/v3/YOUR-PROJECT-ID'))

# Read in early user transaction history
txData = pd.read_csv(infile,header=None,
            names=['block','txhash','address','action','token','decimals',
                   'amount','startingBalance','newBalance'])

# Initialize a new column to store price data
txData['price'] = 0
txData = txData.sort_values(['block','token'])

# Pull historical price data from CoinGecko API
pricedata = dict()
startTimeStamp = w3.eth.getBlock(CompV1deployBlock)['timestamp']
startDate = date.fromtimestamp(startTimeStamp)
endTimeStamp   = w3.eth.getBlock(EarlyUserCutoffBlock)['timestamp']
endDate = date.fromtimestamp(endTimeStamp)
daysToQuery = str((date.today()-startDate).days)
datelist = pd.date_range(startDate,endDate).tolist()
for token in tokenList:
    pricedata[token] = dict()
    apicall  = 'https://api.coingecko.com/api/v3/coins/'+CoinGeckoLabel[token]
    apicall += '/market_chart?vs_currency=usd&days='+daysToQuery+'&interval=daily'
    response = requests.get(apicall)
    apidata = json.loads(response.content)
    i = 0 
    for day in datelist:
        try:
            pricedata[token][day.day] = apidata['prices'][i][1]
        except:
            pricedata[token][day.day] = 0.
        i += 1

# For each tx, get the price of the asset at the specified block
for index, row in txData.iterrows():
    print("Processing tx " + row['txhash'])
    if row['action'] == 'liquidate':
        continue
    newBalance = int(row['newBalance'])
    startingBalance = int(row['startingBalance'])
    block = int(row['block'])
    address = str(row['address'])
    amount = int(row['amount'])
    token = str(row['token'])
    # Get timestamp for this block
    blockInfo = w3.eth.getBlock(block)
    timestamp = blockInfo['timestamp']
    blockdate = date.fromtimestamp(timestamp)
    txData.loc[index,'price'] = pricedata[token][blockdate.day]
    
txData.to_csv(outfile)
