import pandas as pd
import web3
import json
from sys import argv

earlyUserFile = 'CompoundV1.EarlyUserEvents.csv'
outfile = 'CompoundV1.EarlyUserInterest.csv'

txData = pd.read_csv(earlyUserFile,
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


# Get a web3 object pulling data from Infura Ethereum Mainnet RPC
w3 = web3.Web3(web3.Web3.HTTPProvider('https://mainnet.infura.io/v3/YOUR-PROJECT-ID'))

CompV1 = {
  "address"     : '0x3FDA67f7583380E67ef93072294a7fAc882FD7E7',
  "deployBlock" : 6400278,
  "abi"         : 'CompoundV1.abi.json'
}

with open(CompV1["abi"]) as json_file:
    CompoundV1ABI = json.load(json_file)
    MoneyMarketABI = CompoundV1ABI["MoneyMarket"]

MoneyMarket = w3.eth.contract(CompV1["address"],abi=MoneyMarketABI)
CompV1deployBlock      = 6400278
# Cutoff at date of COMP token announcement:
# Using first block found on Feb 26, 2020 UTC:
EarlyUserCutoffBlock = 9555731

# ...sort transaction data by address and then by block
txData = txData.sort_values(['address','block'])

#    This entire calculation needs to be replaced with an
#    analysis that updates the total interest accrued for
#    each (address,asset) pair every time an action takes
#    place on that pair

# Initialize a dataframe to store addresses' interest by token
accruedInterest = txData[['address']]
accruedInterest = pd.DataFrame(accruedInterest['address'].unique(),columns=['address'])
for token in tokenList:
    tokenSupplyInterest = token + 'SupplyInterest'
    tokenBorrowInterest = token + 'BorrowInterest'
    accruedInterest[tokenSupplyInterest] = 0
    accruedInterest[tokenBorrowInterest] = 0

# Compound V1 interest accrual tabulation 
for index, row in txData.iterrows():
    if row['action'] == 'liquidate':
        # Eventually we'll need to bump back one tx and repeat...
        continue
    else:
        newBalance = int(row['newBalance'])
        startingBalance = int(row['startingBalance'])
        block = int(row['block'])
        address = str(row['address'])
        amount = int(row['amount'])
        token = str(row['token'])
        tokenSupplyInterest = token + 'SupplyInterest'
        tokenBorrowInterest = token + 'BorrowInterest'
    if row['action'] == 'supply':
        interest = newBalance - startingBalance - amount
        accruedInterest.loc[accruedInterest['address'] == address,
                            tokenSupplyInterest] += interest 
        #print("Accrued supply interest " + str(interest) + " to " + str(row['address']))
    elif row['action'] == 'withdraw':
        interest = newBalance - startingBalance + amount
        accruedInterest.loc[accruedInterest['address'] == address,
                            tokenSupplyInterest] += interest 
        #print("Accrued supply (redeem) interest " + str(interest) + " to " + str(row['address']))
    elif row['action'] == 'borrow':
        interest = newBalance - startingBalance - amount
        accruedInterest.loc[accruedInterest['address'] == address,
                            tokenBorrowInterest] += interest 
        #print("Accrued borrow interest " + str(interest) + " to " + str(row['address']))
    elif row['action'] == 'repay':
        interest = newBalance - startingBalance + amount
        accruedInterest.loc[accruedInterest['address'] == address,
                            tokenBorrowInterest] += interest 
        #print("Accrued borrow (repay) interest " + str(interest) + " to " + str(row['address']))

# Finally, we need to handle interest associated with any
# outstanding balances at the end of the qualifying period
print("Accruing outstanding interest...")
for index,row in accruedInterest.iterrows():
    # For each address, find any nonzero final newBalances in the txData
    thisAddressTxData = txData[txData['address']==row['address']]
    for token in tokenList:
        thisTokenTxData = thisAddressTxData[thisAddressTxData['token']==token]
        try:
            lastNewBalance = int(thisTokenTxData.tail(1)['newBalance'].values)
        except:
            lastNewBalance = int(0)
        if lastNewBalance != 0:
            # compute interest on outstanding balance
            # from blockDelta to last supply/borrow
            # and interest rate per block at EarlyUserCutoffBlock
            lastTxBlock = thisTokenTxData.tail(1)['block'].values[0]
            blockDelta = int(EarlyUserCutoffBlock - lastTxBlock)
            if (blockDelta < 0):
                continue
            thisAction = thisTokenTxData.tail(1)['action'].values
            for i in range(len(V1Tokens)):
                if V1Tokens[i]['label'] == token:
                    thisToken = V1Tokens[i]
            if thisAction == 'supply' or 'withdraw':
            # This is the current V1 rate; I don't see a way to
            # extract the rate at a specific block in the past
                supplyData = MoneyMarket.functions.markets(thisToken['address']).call()
                # supplyIndex, Mantissa are 5th, 4th index returned by V1 markets()
                supplyIndex = float(supplyData[5])
                supplyRateMantissa = float(supplyData[4])
                newInterestIndex = (1.+supplyRateMantissa*10**(-thisToken['decimals'])*blockDelta)*supplyIndex
                newBalance = lastNewBalance*(newInterestIndex/supplyIndex)
                interest = newBalance - lastNewBalance
                print('reconciling ' + str(interest) + ' ' + thisToken['label'] + ' to ' + row['address'])
                #print(row['address'] + " has " + str(newBalance*10**(-thisToken['decimals'])) + " " + thisToken['label'] + " with residual supply interest of " + str(interest*10**(-thisToken['decimals'])) + " " + thisToken['label'])
                accruedInterest.loc[accruedInterest['address'] == address,
                                    tokenSupplyInterest] += interest 
                #print("Accrued supply interest " + str(interest) + " to " + str(row['address']))
            elif thisAction == 'borrow' or 'repay':
                borrowData = MoneyMarket.functions.markets(thisToken['address']).call()
                # borrowIndex, Mantissa are the 8th, 7th index returned by V1 markets()
                borrowIndex = float(borrowData[8])
                borrowRateMantissa = float(borrowData[7])
                newInterestIndex = (1.+borrowRateMantissa*10**(-thisToken['decimals'])*blockDelta)*borrowIndex
                newBalance = lastNewBalance*(newInterestIndex/supplyIndex)
                interest = newBalance - lastNewBalance
                print('reconciling ' + interest + ' ' + thisToken['label'] + ' to ' + row['address'])
                #print(row['address'] + " has " + str(newBalance*10**(-thisToken['decimals'])) + " " + thisToken['label'] + " with residual supply interest of " + str(interest*10**(-thisToken['decimals'])) + " " + thisToken['label'])
                accruedInterest.loc[accruedInterest['address'] == address,
                                    tokenBorrowInterest] += interest 
                #print("Accrued borrow (repay) interest " + str(interest) + " to " + str(row['address']))
            # We should technically step back recursively to last non-liquidate
            # action if user's last action was a liquidation; this is on the to-do list 

accruedInterest.to_csv(outfile)
