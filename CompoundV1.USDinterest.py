import pandas as pd
import web3
import json
import requests
from datetime import date, timedelta
from sys import argv

earlyUserFile = 'CompoundV1.EarlyUserEvents.csv'
outfile = 'CompoundV1.EarlyUserUSDInterest.csv'

txData = pd.read_csv(earlyUserFile,header=None,skiprows=1,
            names=['block','txhash','address','action','token','decimals',
                   'amount','startingBalance','newBalance'])

tokenList = ['ZRX','BAT','REP','WETH','SAI','ETH','USDC','WBTC','DAI']

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

CompV1 = {
  "address"     : '0x3FDA67f7583380E67ef93072294a7fAc882FD7E7',
  "deployBlock" : 6400278,
  "abi"         : 'CompoundV1.abi.json'
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

# Get a web3 object pulling data from Infura Ethereum Mainnet RPC
w3 = web3.Web3(web3.Web3.HTTPProvider('https://dry-empty-sunset.quiknode.io/36e947d3-a37c-4480-a42a-8a879acbcf51/Lr6bbYqSl6kFkTRn5TG_OY3KOs13qPq0H-pKUtjqiu2XP-YOeyTdTKhb5Z56dQgFQb49acVpR5olMxSuLVznmg==/'))

with open(CompV1["abi"]) as json_file:
    CompoundV1ABI = json.load(json_file)
    MoneyMarketABI = CompoundV1ABI["MoneyMarket"]

MoneyMarket = w3.eth.contract(CompV1["address"],abi=MoneyMarketABI)
CompV1deployBlock      = 6400278
# Cutoff at date of COMP token announcement:
# Using first block found on Feb 26, 2020 UTC:
EarlyUserCutoffBlock = 9555731

# Initialize a new column to store interest data in USD
#txData['USDinterest'] = 0

# ...sort transaction data by address and then by block and token
txData = txData.sort_values(['address','block','token'])

# Initialize a dataframe to store addresses' interest by token
accruedInterest = txData[['address']]
accruedInterest = pd.DataFrame(accruedInterest['address'].unique(),columns=['address'])
for token in tokenList:
    tokenSupplyInterest = token + 'SupplyInterest'
    tokenBorrowInterest = token + 'BorrowInterest'
    accruedInterest[tokenSupplyInterest] = 0
    accruedInterest[tokenBorrowInterest] = 0

# Pull historical price data from CoinGecko API into a dataframe 'pricedata'
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

# Compound V1 interest accrual tabulation 
for index, row in txData.iterrows():
    if row['action'] == 'liquidate':
        continue
    # Extract account status from event log
    newBalance      = float(row['newBalance'])
    startingBalance = float(row['startingBalance'])
    block           = int(row['block'])
    address         = str(row['address'])
    amount          = float(row['amount'])
    token           = str(row['token'])
    tokenSupplyInterest = token + 'SupplyInterest'
    tokenBorrowInterest = token + 'BorrowInterest'
    # Get the dictionary associated with this token
    for i in range(len(V1Tokens)):
        if V1Tokens[i]['label'] == token:
            thisToken = V1Tokens[i]
    # Get timestamp for this block
    blockInfo    = w3.eth.getBlock(block)
    timestamp    = blockInfo['timestamp']
    blockdate    = date.fromtimestamp(timestamp)
    # Get USD conversion factor for this token and date
    convertToUSD = pricedata[token][blockdate.day]*10**(-thisToken['decimals'])
    if row['action'] == 'supply':
        interest = newBalance - startingBalance - amount
        interest = interest*convertToUSD
        accruedInterest.loc[accruedInterest['address'] == address,
                            tokenSupplyInterest] += interest 
        print("Accrued supply interest " + str(interest) + " to " + str(row['address']))
    elif row['action'] == 'withdraw':
        interest = newBalance - startingBalance + amount
        interest = interest*convertToUSD
        accruedInterest.loc[accruedInterest['address'] == address,
                            tokenSupplyInterest] += interest 
        print("Accrued supply (redeem) interest " + str(interest) + " to " + str(row['address']))
    elif row['action'] == 'borrow':
        interest = newBalance - startingBalance - amount
        interest = interest*convertToUSD
        accruedInterest.loc[accruedInterest['address'] == address,
                            tokenBorrowInterest] += interest 
        print("Accrued borrow interest " + str(interest) + " to " + str(row['address']))
    elif row['action'] == 'repay':
        interest = newBalance - startingBalance + amount
        interest = interest*convertToUSD
        accruedInterest.loc[accruedInterest['address'] == address,
                            tokenBorrowInterest] += interest 
        print("Accrued borrow (repay) interest " + str(interest) + " to " + str(row['address']))

# Finally, we need to handle interest associated with any
# outstanding balances at the end of the qualifying period;
# This is a bit harder because we don't have contract events to work with

# Get timestamp for early user cutoff 
blockInfo    = w3.eth.getBlock(EarlyUserCutoffBlock)
timestamp    = blockInfo['timestamp']
blockdate    = date.fromtimestamp(timestamp)
print("Accruing outstanding interest...")
for index,row in accruedInterest.iterrows():
    # For each address, find any nonzero final newBalances in the txData,
    # including both supply/withdraw and borrow/repay balances
    thisAddressTxData = txData[txData['address']==row['address']]
    for token in tokenList:
        # Get the dictionary associated with this token
        for i in range(len(V1Tokens)):
            if V1Tokens[i]['label'] == token:
                thisToken = V1Tokens[i]
        # Get USD conversion factor for this token and date
        convertToUSD = pricedata[token][blockdate.day]*10**(-thisToken['decimals'])
        thisTokenTxData = thisAddressTxData[thisAddressTxData['token']==token]
        if thisTokenTxData.empty:
            continue
        #print(thisTokenTxData)
        txCount = 0
        foundSupplyWithdraw = False
        foundBorrowRepay    = False
        while foundSupplyWithdraw == False or foundBorrowRepay == False:
            #print("Still looking for a latest supply or latest withdraw...")
            txCount += 1
            if thisTokenTxData.empty:
                break
            if len(thisTokenTxData.tail(txCount)['newBalance'].values) >= txCount:
                break
            try:
                lastNewBalance = int(thisTokenTxData.tail(txCount)['newBalance'].values[0])     ## Instead of values[0] and looping bkwds,
                #print("lastNewBalance = ", lastNewBalance)                                      ## can we grab all values and find last
            except:                                                                             ## supply/withdraw and borrow/repay directly?
                #print(thisTokenTxData.tail(txCount)['newBalance'].values[0])
                foundSupplyWithdraw = True
                foundBorrowRepay = True
            if lastNewBalance != 0:
                # compute interest on outstanding balance
                # from blockDelta to last supply/borrow
                # and interest rate per block at EarlyUserCutoffBlock
                lastTxBlock = thisTokenTxData.tail(txCount)['block'].values[0]
                blockDelta = int(EarlyUserCutoffBlock - lastTxBlock)
                if (blockDelta < 0):
                    continue
                thisAction = thisTokenTxData.tail(1)['action'].values
                if thisAction == 'liquidate':
                    continue
                elif thisAction == 'supply' or 'withdraw':
                    FoundSupplyWithdraw = True
                # Using the current V1 rate; I don't see a way to
                # extract the rate at a specific block in the past
                    supplyData = MoneyMarket.functions.markets(thisToken['address']).call()
                    # supplyIndex, Mantissa are 5th, 4th index returned by V1 markets()
                    supplyIndex = float(supplyData[5])
                    supplyRateMantissa = float(supplyData[4])
                    newInterestIndex = (1.+supplyRateMantissa*10**(-thisToken['decimals'])*blockDelta)*supplyIndex
                    newBalance = lastNewBalance*(newInterestIndex/supplyIndex)
                    interest = newBalance - lastNewBalance
                    interest = interest*convertToUSD
                    #print('reconciling ' + str(interest) + ' ' + thisToken['label'] + ' to ' + row['address'])
                    print(row['address'] + " has " + str(newBalance*10**(-thisToken['decimals'])) + " " + thisToken['label'] + " with residual supply interest of " + str(interest*10**(-thisToken['decimals'])) + " " + thisToken['label'])
                    accruedInterest.loc[accruedInterest['address'] == address,
                                        tokenSupplyInterest] += interest 
                    #print("Accrued supply interest " + str(interest) + " to " + str(row['address']))
                elif thisAction == 'borrow' or 'repay':
                    FoundBorrowRepay = True
                    borrowData = MoneyMarket.functions.markets(thisToken['address']).call()
                    # borrowIndex, Mantissa are the 8th, 7th index returned by V1 markets()
                    borrowIndex = float(borrowData[8])
                    borrowRateMantissa = float(borrowData[7])
                    newInterestIndex = (1.+borrowRateMantissa*10**(-thisToken['decimals'])*blockDelta)*borrowIndex
                    newBalance = lastNewBalance*(newInterestIndex/supplyIndex)
                    interest = newBalance - lastNewBalance
                    interest = interest*convertToUSD
                    print('reconciling ' + interest + ' ' + thisToken['label'] + ' to ' + row['address'])
                    print(row['address'] + " has " + str(newBalance*10**(-thisToken['decimals'])) + " " + thisToken['label'] + " with residual borrow interest of " + str(interest*10**(-thisToken['decimals'])) + " " + thisToken['label'])
                    accruedInterest.loc[accruedInterest['address'] == address,
                                        tokenBorrowInterest] += interest 
                    #print("Accrued borrow (repay) interest " + str(interest) + " to " + str(row['address']))
            else:
                thisAction = thisTokenTxData.tail(1)['action'].values
                if thisAction == 'liquidate':
                    continue
                elif thisAction == 'supply' or 'withdraw':
                    foundSupplyWithdraw = True
                elif thisAction == 'borrow' or 'repay':
                    foundBorrowRepay = True
accruedInterest.to_csv(outfile)
